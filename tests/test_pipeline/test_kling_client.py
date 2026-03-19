# PC-01: Kling 2.6 client tests (TDD)
"""Tests for KlingClient — submit, poll, download, rate limiting."""

from unittest.mock import MagicMock, patch, mock_open

import pytest


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "test-api-key-123")


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.content = b"fake-video-bytes"
        self.ok = status_code < 400

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        yield self.content


def test_client_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("KLING_API_KEY", raising=False)
    from generate_video.kling_client import KlingClient
    with pytest.raises(RuntimeError, match="KLING_API_KEY"):
        KlingClient()


def test_client_init_with_key():
    from generate_video.kling_client import KlingClient
    client = KlingClient()
    assert client.api_key == "test-api-key-123"
    assert "klingapi.com" in client.base_url


@patch("generate_video.kling_client.requests.post")
def test_submit_text2video_returns_task_id(mock_post):
    mock_post.return_value = FakeResponse({"task_id": "task_abc123"}, 200)

    from generate_video.kling_client import KlingClient
    client = KlingClient()
    task_id = client.submit_text2video(
        prompt="A student studying at a desk",
        duration=10,
        aspect_ratio="9:16",
    )

    assert task_id == "task_abc123"
    call_args = mock_post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    assert body["model"] == "kling-v2.6-pro"
    assert body["prompt"] == "A student studying at a desk"
    assert body["duration"] == 10
    assert body["aspect_ratio"] == "9:16"
    assert "Authorization" in (call_args.kwargs.get("headers") or call_args[1].get("headers"))


@patch("generate_video.kling_client.requests.post")
def test_submit_with_audio_and_negative_prompt(mock_post):
    mock_post.return_value = FakeResponse({"task_id": "task_xyz"}, 200)

    from generate_video.kling_client import KlingClient
    client = KlingClient()
    client.submit_text2video(
        prompt="A parent helping student",
        duration=5,
        aspect_ratio="16:9",
        audio=True,
        negative_prompt="blur, logos",
    )

    body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert body["sound"] is True
    assert body["negative_prompt"] == "blur, logos"


@patch("generate_video.kling_client.requests.get")
def test_poll_task_completed(mock_get):
    mock_get.return_value = FakeResponse({
        "task_id": "task_1",
        "status": "completed",
        "url": "https://cdn.kling.ai/video.mp4",
    })

    from generate_video.kling_client import KlingClient
    client = KlingClient()
    result = client.poll_task("task_1", timeout_seconds=10, poll_interval=0.1)

    assert result.status == "completed"
    assert result.video_url == "https://cdn.kling.ai/video.mp4"
    assert result.error_message is None


@patch("generate_video.kling_client.requests.get")
def test_poll_task_failed(mock_get):
    mock_get.return_value = FakeResponse({
        "task_id": "task_2",
        "status": "failed",
        "error": {"code": 1001, "message": "Content policy violation"},
    })

    from generate_video.kling_client import KlingClient
    client = KlingClient()
    result = client.poll_task("task_2", timeout_seconds=10, poll_interval=0.1)

    assert result.status == "failed"
    assert "Content policy" in result.error_message


@patch("generate_video.kling_client.time.sleep")
@patch("generate_video.kling_client.requests.get")
def test_poll_task_waits_for_processing(mock_get, mock_sleep):
    responses = [
        FakeResponse({"task_id": "t", "status": "processing"}),
        FakeResponse({"task_id": "t", "status": "processing"}),
        FakeResponse({"task_id": "t", "status": "completed", "url": "https://cdn.kling.ai/v.mp4"}),
    ]
    mock_get.side_effect = responses

    from generate_video.kling_client import KlingClient
    client = KlingClient()
    result = client.poll_task("t", timeout_seconds=60, poll_interval=1)

    assert result.status == "completed"
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


@patch("generate_video.kling_client.time.time")
@patch("generate_video.kling_client.time.sleep")
@patch("generate_video.kling_client.requests.get")
def test_poll_task_timeout(mock_get, mock_sleep, mock_time):
    mock_get.return_value = FakeResponse({"task_id": "t", "status": "processing"})
    mock_time.side_effect = [0, 5, 10, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 125]

    from generate_video.kling_client import KlingClient, VideoGenerationError
    client = KlingClient()
    with pytest.raises(VideoGenerationError, match="timed out"):
        client.poll_task("t", timeout_seconds=120, poll_interval=1)


@patch("generate_video.kling_client.Path")
@patch("generate_video.kling_client.requests.get")
def test_download_video(mock_get, mock_path_cls):
    mock_get.return_value = FakeResponse({}, 200)
    mock_get.return_value.iter_content = lambda chunk_size: [b"fake-mp4-data"]

    mock_path_inst = MagicMock()
    mock_path_inst.parent.mkdir = MagicMock()
    mock_path_inst.exists.return_value = True
    mock_path_inst.stat.return_value = MagicMock(st_size=1024)
    mock_path_cls.return_value = mock_path_inst

    from generate_video.kling_client import KlingClient
    client = KlingClient()

    with patch("builtins.open", mock_open()) as m:
        path = client.download_video("https://cdn.kling.ai/v.mp4", "/tmp/test.mp4")

    assert path == "/tmp/test.mp4"
    m.assert_called_once_with("/tmp/test.mp4", "wb")


def test_rate_limiter_waits_when_at_capacity():
    from generate_video.kling_client import KlingClient
    client = KlingClient(rpm=2)
    client._call_timestamps.clear()

    base = 1000.0
    client._call_timestamps.extend([base - 10, base - 5])

    call_count = [0]

    def fake_time():
        call_count[0] += 1
        if call_count[0] <= 2:
            return base
        return base + 61

    with patch("generate_video.kling_client.time.sleep") as mock_sleep:
        with patch("generate_video.kling_client.time.time", side_effect=fake_time):
            client._rate_limit_wait()

    assert mock_sleep.called


def test_rate_limiter_no_wait_when_under_capacity():
    from generate_video.kling_client import KlingClient
    client = KlingClient(rpm=10)
    client._call_timestamps.clear()

    with patch("generate_video.kling_client.time.sleep") as mock_sleep:
        client._rate_limit_wait()

    mock_sleep.assert_not_called()
