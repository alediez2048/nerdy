"""Tests for FalVideoClient and the video client factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── FalVideoClient tests ───────────────────────────────────────────────


def test_extract_fal_video_url_nested_data() -> None:
    from generate_video.fal_client import _extract_fal_video_url

    url = _extract_fal_video_url(
        {"data": {"video": {"url": "https://cdn.example.com/v.mp4"}}}
    )
    assert url == "https://cdn.example.com/v.mp4"


class TestFalVideoClient:
    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_init_sets_model_used(self) -> None:
        from generate_video.fal_client import FalVideoClient

        client = FalVideoClient(api_key="test-key")
        assert client.model_used == "fal-ai/veo3"

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_init_custom_model(self) -> None:
        from generate_video.fal_client import FalVideoClient

        client = FalVideoClient(api_key="test-key", model="fal-ai/kling-video/v2")
        assert client.model_used == "fal-ai/kling-video/v2"

    def test_init_raises_without_key(self) -> None:
        from generate_video.fal_client import FalVideoClient

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="FAL_KEY"):
                FalVideoClient(api_key="")

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_normalize_duration(self) -> None:
        from generate_video.fal_client import FalVideoClient

        client = FalVideoClient(api_key="test-key")
        assert client.normalize_duration(4) == 4
        assert client.normalize_duration(6) == 6
        assert client.normalize_duration(8) == 8
        assert client.normalize_duration(10) == 8
        assert client.normalize_duration(3) == 4

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_normalize_aspect_ratio(self) -> None:
        from generate_video.fal_client import FalVideoClient

        client = FalVideoClient(api_key="test-key")
        assert client.normalize_aspect_ratio("9:16") == "9:16"
        assert client.normalize_aspect_ratio("16:9") == "16:9"
        assert client.normalize_aspect_ratio("1:1") == "9:16"

    @patch("generate_video.fal_client.httpx")
    @patch("generate_video.fal_client.fal_client")
    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_generate_video_success(
        self, mock_fal: MagicMock, mock_httpx: MagicMock, tmp_path: Path
    ) -> None:
        from generate_video.fal_client import FalVideoClient

        output_path = str(tmp_path / "result.mp4")
        mock_fal.subscribe.return_value = {
            "video": {"url": "https://fal.media/test.mp4"}
        }
        mock_resp = MagicMock()
        mock_resp.content = b"fake-video-data"
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        client = FalVideoClient(api_key="test-key")
        result = client.generate_video(
            prompt="A student studies for the SAT",
            duration=8,
            aspect_ratio="9:16",
            output_path=output_path,
        )

        assert result == output_path
        assert Path(output_path).exists()
        mock_fal.subscribe.assert_called_once()
        args = mock_fal.subscribe.call_args
        assert args[0][0] == "fal-ai/veo3"
        assert args[1]["arguments"]["duration"] == "8s"
        assert args[1]["arguments"]["aspect_ratio"] == "9:16"

    @patch("generate_video.fal_client.httpx")
    @patch("generate_video.fal_client.fal_client")
    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_generate_video_includes_negative_prompt(
        self, mock_fal: MagicMock, mock_httpx: MagicMock, tmp_path: Path
    ) -> None:
        from generate_video.fal_client import FalVideoClient

        output_path = str(tmp_path / "result.mp4")
        mock_fal.subscribe.return_value = {
            "video": {"url": "https://fal.media/test.mp4"}
        }
        mock_resp = MagicMock()
        mock_resp.content = b"fake-data"
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        client = FalVideoClient(api_key="test-key")
        client.generate_video(
            prompt="A student studies",
            negative_prompt="brand logos, text",
            output_path=output_path,
        )

        args = mock_fal.subscribe.call_args[1]["arguments"]
        assert args["prompt"] == "A student studies"
        assert args["negative_prompt"] == "brand logos, text"


# ── Protocol conformance ────────────────────────────────────────────────


class TestProtocolConformance:
    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_fal_client_is_video_generation_client(self) -> None:
        from generate_video.fal_client import FalVideoClient
        from generate_video.video_client import VideoGenerationClient

        assert isinstance(FalVideoClient(api_key="test-key"), VideoGenerationClient)

    def test_veo_client_is_video_generation_client(self) -> None:
        try:
            from generate_video.veo_client import VeoClient
        except ImportError:
            pytest.skip("google-genai not installed")
        from generate_video.video_client import VideoGenerationClient

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            assert isinstance(VeoClient(api_key="test-key"), VideoGenerationClient)


# ── Factory tests ──────────────────────────────────────────────────────


class TestBuildVideoClient:
    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_explicit_fal_provider(self) -> None:
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            client = factory_mod.build_video_client(provider="fal")
            assert isinstance(client, FalVideoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_fal_model_kwarg_selects_endpoint(self) -> None:
        """Session config video_fal_model maps to FalVideoClient.model_used / subscribe id."""
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            client = factory_mod.build_video_client(
                provider="fal",
                model="fal-ai/kling-video/v2.1/standard",
            )
            assert isinstance(client, FalVideoClient)
            assert client.model_used == "fal-ai/kling-video/v2.1/standard"

    def test_explicit_veo_provider(self) -> None:
        try:
            from generate_video.veo_client import VeoClient  # noqa: F401
        except ImportError:
            pytest.skip("google-genai not installed")
        import generate_video.factory as factory_mod

        with (
            patch.object(factory_mod, "_load_config_provider", return_value=None),
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        ):
            client = factory_mod.build_video_client(provider="veo")
            assert isinstance(client, VeoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_default_is_fal(self) -> None:
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            client = factory_mod.build_video_client(provider=None)
            assert isinstance(client, FalVideoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_config_yaml_provider(self) -> None:
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value="fal"):
            client = factory_mod.build_video_client(provider=None)
            assert isinstance(client, FalVideoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key", "VIDEO_PROVIDER": "fal"})
    def test_env_var_fallback(self) -> None:
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            client = factory_mod.build_video_client(provider=None)
            assert isinstance(client, FalVideoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_invalid_provider_falls_back_to_fal(self) -> None:
        import generate_video.factory as factory_mod
        from generate_video.fal_client import FalVideoClient

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            client = factory_mod.build_video_client(provider="nonexistent")
            assert isinstance(client, FalVideoClient)

    def test_session_provider_overrides_config(self) -> None:
        """Session-level provider takes precedence over config.yaml."""
        try:
            from generate_video.veo_client import VeoClient  # noqa: F401
        except ImportError:
            pytest.skip("google-genai not installed")
        import generate_video.factory as factory_mod

        with (
            patch.object(factory_mod, "_load_config_provider", return_value="fal"),
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        ):
            client = factory_mod.build_video_client(provider="veo")
            assert isinstance(client, VeoClient)

    @patch.dict("os.environ", {"FAL_KEY": "test-key"})
    def test_precedence_session_over_config(self) -> None:
        """Session provider overrides config.yaml provider."""
        import generate_video.factory as factory_mod

        with patch.object(factory_mod, "_load_config_provider", return_value="veo"):
            assert factory_mod._resolve_provider("fal") == "fal"

    @patch.dict("os.environ", {"VIDEO_PROVIDER": "veo"})
    def test_precedence_env_var(self) -> None:
        """Env var is used when session and config are both None."""
        import generate_video.factory as factory_mod

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            assert factory_mod._resolve_provider(None) == "veo"

    @patch.dict("os.environ", {}, clear=True)
    def test_precedence_default_fal(self) -> None:
        """Without any config, default is fal."""
        import generate_video.factory as factory_mod

        with patch.object(factory_mod, "_load_config_provider", return_value=None):
            assert factory_mod._resolve_provider(None) == "fal"
