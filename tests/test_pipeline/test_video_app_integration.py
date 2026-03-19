"""PC-03: App integration tests — video task routing, assembler, export."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


from output.video_assembler import (
    VideoAssembledAd,
    assemble_video_ad,
    export_video_ads,
)


# ── assemble_video_ad tests ────────────────────────────────────────────


def _write_ledger_events(ledger_path: str, events: list[dict]) -> None:
    with open(ledger_path, "w") as f:
        for ev in events:
            ev.setdefault("timestamp", "2026-03-18T00:00:00")
            ev.setdefault("checkpoint_id", "test-ckpt")
            ev.setdefault("brief_id", "brief_001")
            ev.setdefault("cycle_number", 0)
            ev.setdefault("action", "test")
            ev.setdefault("tokens_consumed", 0)
            ev.setdefault("model_used", "test")
            ev.setdefault("seed", "42")
            f.write(json.dumps(ev) + "\n")


class TestAssembleVideoAd:
    def test_assemble_with_video_selected(self, tmp_path: Path) -> None:
        ledger = str(tmp_path / "ledger.jsonl")
        video_path = str(tmp_path / "test.mp4")
        Path(video_path).write_bytes(b"fake-video-data")

        _write_ledger_events(ledger, [
            {
                "event_type": "AdGenerated",
                "ad_id": "ad_001_c0",
                "outputs": {
                    "primary_text": "Boost your SAT score",
                    "headline": "Expert Tutoring",
                    "description": "Start today",
                    "cta_button": "Learn More",
                },
            },
            {
                "event_type": "AdEvaluated",
                "ad_id": "ad_001_c0",
                "scores": {"clarity": 8.0, "value_proposition": 7.5},
            },
            {
                "event_type": "VideoSelected",
                "ad_id": "ad_001_c0",
                "outputs": {
                    "winner_video_path": video_path,
                    "composite_score": 0.85,
                    "attribute_pass_pct": 1.0,
                    "coherence_avg": 5.5,
                },
            },
        ])

        result = assemble_video_ad("ad_001_c0", ledger)

        assert isinstance(result, VideoAssembledAd)
        assert result.ad_id == "ad_001_c0"
        assert result.primary_text == "Boost your SAT score"
        assert result.headline == "Expert Tutoring"
        assert result.cta_button == "Learn More"
        assert result.winning_video_path == video_path
        assert result.formats == ["copy", "video"]
        assert result.video_scores is not None
        assert result.video_scores["composite_score"] == 0.85

    def test_assemble_with_video_blocked(self, tmp_path: Path) -> None:
        ledger = str(tmp_path / "ledger.jsonl")

        _write_ledger_events(ledger, [
            {
                "event_type": "AdGenerated",
                "ad_id": "ad_002_c0",
                "outputs": {
                    "primary_text": "SAT prep",
                    "headline": "Get started",
                    "description": "Desc",
                    "cta_button": "Sign Up",
                },
            },
            {
                "event_type": "VideoBlocked",
                "ad_id": "ad_002_c0",
                "outputs": {"reason": "all_variants_failed"},
            },
        ])

        result = assemble_video_ad("ad_002_c0", ledger)

        assert result.winning_video_path is None
        assert result.formats == ["copy"]
        assert result.video_scores is None

    def test_assemble_missing_ad(self, tmp_path: Path) -> None:
        ledger = str(tmp_path / "ledger.jsonl")
        Path(ledger).write_text("")

        result = assemble_video_ad("nonexistent", ledger)
        assert result.primary_text == ""
        assert result.winning_video_path is None
        assert result.formats == ["copy"]


# ── export_video_ads tests ─────────────────────────────────────────────


class TestExportVideoAds:
    def test_export_creates_structure(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path / "export")
        video_path = str(tmp_path / "source.mp4")
        Path(video_path).write_bytes(b"fake-mp4-content")

        ads = [
            VideoAssembledAd(
                ad_id="ad_001_c0",
                brief_id="brief_001",
                primary_text="Boost SAT",
                headline="Expert Help",
                description="Start today",
                cta_button="Learn More",
                winning_video_path=video_path,
                video_scores={"composite_score": 0.85},
                formats=["copy", "video"],
                audience="parents",
                campaign_goal="conversion",
                persona="suburban_optimizer",
                seed=12345,
            ),
        ]

        dirs = export_video_ads(ads, output_dir)

        assert len(dirs) == 1
        ad_dir = Path(dirs[0])
        assert ad_dir.exists()
        assert (ad_dir / "metadata.json").exists()
        metadata = json.loads((ad_dir / "metadata.json").read_text())
        assert metadata["ad_id"] == "ad_001_c0"
        assert metadata["primary_text"] == "Boost SAT"

    def test_export_copies_video_file(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path / "export")
        video_path = str(tmp_path / "video.mp4")
        content = b"real-video-bytes-here"
        Path(video_path).write_bytes(content)

        ads = [
            VideoAssembledAd(
                ad_id="ad_002_c0",
                brief_id="brief_002",
                primary_text="Test",
                headline="Test",
                description="Test",
                cta_button="CTA",
                winning_video_path=video_path,
                video_scores={"composite_score": 0.7},
                formats=["copy", "video"],
                audience="students",
                campaign_goal="awareness",
                persona="auto",
                seed=99,
            ),
        ]

        dirs = export_video_ads(ads, output_dir)
        ad_dir = Path(dirs[0])
        video_files = list(ad_dir.glob("*.mp4"))
        assert len(video_files) == 1
        assert video_files[0].read_bytes() == content

    def test_export_copy_only_no_video_file(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path / "export")

        ads = [
            VideoAssembledAd(
                ad_id="ad_003_c0",
                brief_id="brief_003",
                primary_text="Copy only",
                headline="No video",
                description="Desc",
                cta_button="CTA",
                winning_video_path=None,
                video_scores=None,
                formats=["copy"],
                audience="parents",
                campaign_goal="conversion",
                persona="auto",
                seed=0,
            ),
        ]

        dirs = export_video_ads(ads, output_dir)
        ad_dir = Path(dirs[0])
        assert (ad_dir / "metadata.json").exists()
        video_files = list(ad_dir.glob("*.mp4"))
        assert len(video_files) == 0


# ── Celery task routing tests ──────────────────────────────────────────


class TestCeleryTaskRouting:
    @patch("app.workers.tasks.pipeline_task.SessionLocal")
    @patch("app.workers.tasks.pipeline_task.init_db")
    def test_video_session_routes_to_video_pipeline(
        self, mock_init_db: MagicMock, mock_session_local: MagicMock
    ) -> None:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_row = MagicMock()
        mock_row.config = {"session_type": "video", "video_count": 2}
        mock_row.session_id = "sess_video_test"
        mock_row.ledger_path = "/tmp/test_ledger.jsonl"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        with patch(
            "app.workers.tasks.pipeline_task._run_video_pipeline"
        ) as mock_video:
            mock_video.return_value = {
                "videos_generated": 2,
                "videos_selected": 1,
                "videos_blocked": 1,
            }

            from app.workers.tasks.pipeline_task import run_pipeline_session

            result = run_pipeline_session("sess_video_test")

            mock_video.assert_called_once()
            assert result["status"] == "completed"

    @patch("app.workers.tasks.pipeline_task.SessionLocal")
    @patch("app.workers.tasks.pipeline_task.init_db")
    def test_image_session_routes_to_image_pipeline(
        self, mock_init_db: MagicMock, mock_session_local: MagicMock
    ) -> None:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_row = MagicMock()
        mock_row.config = {"session_type": "image", "ad_count": 5}
        mock_row.session_id = "sess_image_test"
        mock_row.ledger_path = "/tmp/test_ledger.jsonl"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        with patch(
            "app.workers.tasks.pipeline_task._run_image_pipeline"
        ) as mock_image:
            mock_image.return_value = {
                "ads_generated": 5,
                "ads_published": 3,
            }

            from app.workers.tasks.pipeline_task import run_pipeline_session

            run_pipeline_session("sess_image_test")

            mock_image.assert_called_once()

    @patch("app.workers.tasks.pipeline_task.SessionLocal")
    @patch("app.workers.tasks.pipeline_task.init_db")
    def test_missing_session_type_defaults_to_image(
        self, mock_init_db: MagicMock, mock_session_local: MagicMock
    ) -> None:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_row = MagicMock()
        mock_row.config = {"ad_count": 5}
        mock_row.session_id = "sess_old"
        mock_row.ledger_path = "/tmp/test_ledger.jsonl"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        with patch(
            "app.workers.tasks.pipeline_task._run_image_pipeline"
        ) as mock_image:
            mock_image.return_value = {
                "ads_generated": 5,
                "ads_published": 3,
            }

            from app.workers.tasks.pipeline_task import run_pipeline_session

            run_pipeline_session("sess_old")
            mock_image.assert_called_once()


# ── Progress event tests ───────────────────────────────────────────────


class TestVideoProgressEvents:
    def test_video_progress_stages_defined(self) -> None:
        from app.workers.progress import (
            VIDEO_AD_COMPLETE,
            VIDEO_AD_START,
            VIDEO_EVALUATING,
            VIDEO_GENERATING,
            VIDEO_PIPELINE_COMPLETE,
            VIDEO_PIPELINE_START,
        )

        assert VIDEO_PIPELINE_START == "video_pipeline_start"
        assert VIDEO_AD_START == "video_ad_start"
        assert VIDEO_GENERATING == "video_generating"
        assert VIDEO_EVALUATING == "video_evaluating"
        assert VIDEO_AD_COMPLETE == "video_ad_complete"
        assert VIDEO_PIPELINE_COMPLETE == "video_pipeline_complete"
