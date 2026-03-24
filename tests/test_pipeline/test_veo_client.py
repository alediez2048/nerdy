"""Tests for VeoClient live integration wrapper."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")


def test_client_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from generate_video.veo_client import VeoClient

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        VeoClient()


@patch("generate_video.veo_client.genai.Client")
def test_generate_video_saves_file_and_normalizes_request(mock_client_cls, tmp_path):
    output_path = tmp_path / "generated.mp4"

    class FakeVideoFile:
        def save(self, path: str) -> None:
            Path(path).write_bytes(b"fake-mp4-data")

    mock_client = MagicMock()
    mock_client.files.download = MagicMock()
    mock_client.models.generate_videos.return_value = MagicMock(
        done=True,
        error=None,
        response=MagicMock(
            generated_videos=[MagicMock(video=FakeVideoFile())]
        ),
    )
    mock_client_cls.return_value = mock_client

    from generate_video.veo_client import VeoClient

    client = VeoClient()
    saved = client.generate_video(
        prompt="A student studies for the SAT",
        duration=10,
        aspect_ratio="1:1",
        output_path=str(output_path),
    )

    assert saved == str(output_path)
    assert output_path.exists()

    kwargs = mock_client.models.generate_videos.call_args.kwargs
    assert kwargs["model"] == "veo-3.1-fast-generate-preview"
    assert kwargs["config"].duration_seconds == 8
    assert kwargs["config"].aspect_ratio == "9:16"


def test_normalize_duration_forces_known_good_veo_length():
    from generate_video.veo_client import VeoClient

    client = VeoClient()

    assert client.normalize_duration(5) == 8
    assert client.normalize_duration(8) == 8
    assert client.normalize_duration(10) == 8


@patch("generate_video.veo_client.retry_with_backoff", side_effect=lambda func: func())
@patch("generate_video.veo_client.genai.Client")
def test_generate_video_retries_silent_after_audio_quota_error(mock_client_cls, mock_retry, tmp_path):
    output_path = tmp_path / "generated.mp4"

    class FakeVideoFile:
        def save(self, path: str) -> None:
            Path(path).write_bytes(b"fake-mp4-data")

    quota_error = Exception("429 RESOURCE_EXHAUSTED")
    success_operation = MagicMock(
        done=True,
        error=None,
        response=MagicMock(
            generated_videos=[MagicMock(video=FakeVideoFile())]
        ),
    )

    mock_client = MagicMock()
    mock_client.files.download = MagicMock()
    mock_client.models.generate_videos.side_effect = [quota_error, success_operation]
    mock_client_cls.return_value = mock_client

    from generate_video.veo_client import VeoClient

    client = VeoClient()
    saved = client.generate_video(
        prompt="A student studies for the SAT",
        duration=8,
        aspect_ratio="9:16",
        audio=True,
        negative_prompt="brand logos",
        output_path=str(output_path),
    )

    assert saved == str(output_path)
    assert output_path.exists()
    assert mock_client.models.generate_videos.call_count == 2
    first_prompt = mock_client.models.generate_videos.call_args_list[0].kwargs["prompt"]
    second_prompt = mock_client.models.generate_videos.call_args_list[1].kwargs["prompt"]
    assert "Audio: silent." not in first_prompt
    assert "Audio: silent." in second_prompt
