# PC-01: Video spec builder tests (TDD)
"""Tests for VideoSpec dataclass, build_video_spec, and build_kling_prompt."""

from unittest.mock import patch



def _make_config(**overrides):
    """Build a minimal session config dict for testing."""
    base = {
        "session_type": "video",
        "audience": "parents",
        "campaign_goal": "conversion",
        "persona": "auto",
        "key_message": "Raise your child's SAT score by 200+ points",
        "video_count": 3,
        "video_duration": 10,
        "video_audio_mode": "silent",
        "video_aspect_ratio": "9:16",
        "video_scene": "",
        "video_visual_style": "",
        "video_camera_movement": "",
        "video_subject_action": "",
        "video_setting": "",
        "video_lighting_mood": "",
        "video_audio_detail": "",
        "video_color_palette": "",
        "video_negative_prompt": "",
    }
    base.update(overrides)
    return base


def _make_brief(**overrides):
    base = {
        "brief_id": "brief_001",
        "product": "SAT Tutoring",
        "audience": "parents",
        "key_message": "Raise your child's SAT score",
        "key_benefit": "personalized 1-on-1 expert tutoring",
        "emotional_angles": ["aspiration"],
    }
    base.update(overrides)
    return base


def _make_copy(**overrides):
    base = {
        "primary_text": "Your child deserves expert SAT guidance.",
        "headline": "200+ Point SAT Improvement",
        "cta_button": "Start Free Assessment",
    }
    base.update(overrides)
    return base


# --- VideoSpec dataclass ---


def test_video_spec_fields():
    from generate_video.video_spec import VideoSpec
    spec = VideoSpec(
        scene="A student studying",
        visual_style="UGC realistic",
        camera_movement="handheld",
        subject_action="Student opens laptop",
        setting="Home study area",
        lighting_mood="Natural soft light",
        audio_mode="silent",
        audio_detail="",
        color_palette="#17e2ea, #0a2240",
        negative_prompt="no logos",
        duration=10,
        aspect_ratio="9:16",
        text_overlay_sequence=["Hook", "Value", "CTA"],
        persona="auto",
        campaign_goal="conversion",
    )
    assert spec.scene == "A student studying"
    assert spec.duration == 10
    assert len(spec.text_overlay_sequence) == 3


# --- build_video_spec with explicit fields ---


def test_build_video_spec_explicit_fields():
    """When user fills in all advanced fields, they pass through directly."""
    from generate_video.video_spec import build_video_spec

    config = _make_config(
        video_scene="Parent and student at kitchen table",
        video_visual_style="cinematic, warm tones",
        video_camera_movement="dolly-in",
        video_subject_action="Student opens SAT results",
        video_setting="Bright kitchen, morning",
        video_lighting_mood="Warm golden hour",
        video_audio_detail="ambient kitchen sounds",
        video_color_palette="#17e2ea, #0a2240",
        video_negative_prompt="no text, no logos",
    )
    brief = _make_brief()
    copy = _make_copy()

    spec = build_video_spec(brief, config, copy)

    assert spec.scene == "Parent and student at kitchen table"
    assert spec.visual_style == "cinematic, warm tones"
    assert spec.camera_movement == "dolly-in"
    assert spec.negative_prompt == "no text, no logos"
    assert spec.duration == 10
    assert spec.aspect_ratio == "9:16"
    assert spec.text_overlay_sequence[0] == copy["primary_text"]


# --- build_video_spec with empty fields (auto-derive) ---


@patch("generate_video.video_spec._call_gemini_for_video_spec")
def test_build_video_spec_auto_derive(mock_gemini):
    """When fields are empty, auto-derive from persona using Gemini Flash."""
    mock_gemini.return_value = {
        "scene": "Auto-generated scene",
        "visual_style": "UGC realistic",
        "camera_movement": "handheld",
        "subject_action": "Student reviews practice test",
        "setting": "Home study area",
        "lighting_mood": "Natural afternoon light",
        "audio_detail": "",
        "color_palette": "#17e2ea",
    }

    from generate_video.video_spec import build_video_spec

    config = _make_config()
    brief = _make_brief()
    copy = _make_copy()

    spec = build_video_spec(brief, config, copy)

    assert spec.scene == "Auto-generated scene"
    assert mock_gemini.called


# --- Persona mapping ---


def test_persona_mapping_athlete():
    """athlete_recruit persona produces fast-paced, competitive spec."""
    from generate_video.video_spec import _PERSONA_VIDEO_DIRECTION
    direction = _PERSONA_VIDEO_DIRECTION["athlete_recruit"]
    assert "competitive" in direction.lower() or "fast" in direction.lower()


def test_persona_mapping_suburban():
    from generate_video.video_spec import _PERSONA_VIDEO_DIRECTION
    direction = _PERSONA_VIDEO_DIRECTION["suburban_optimizer"]
    assert "calm" in direction.lower() or "organized" in direction.lower()


def test_persona_mapping_produces_different_specs():
    """Different personas produce different direction strings."""
    from generate_video.video_spec import _PERSONA_VIDEO_DIRECTION
    athlete = _PERSONA_VIDEO_DIRECTION["athlete_recruit"]
    neurodivergent = _PERSONA_VIDEO_DIRECTION["neurodivergent_advocate"]
    assert athlete != neurodivergent


# --- build_kling_prompt ---


def test_build_kling_prompt_structure():
    from generate_video.video_spec import VideoSpec, build_kling_prompt
    spec = VideoSpec(
        scene="Parent and student celebrating SAT score",
        visual_style="UGC realistic, shot on phone",
        camera_movement="handheld tracking",
        subject_action="Student opens laptop and sees improved score, parent hugs them",
        setting="Bright home study area, afternoon sunlight",
        lighting_mood="Natural, warm, encouraging",
        audio_mode="silent",
        audio_detail="",
        color_palette="#17e2ea, #0a2240",
        negative_prompt="no text, no logos",
        duration=10,
        aspect_ratio="9:16",
        text_overlay_sequence=["Hook line", "Value prop", "CTA button"],
        persona="suburban_optimizer",
        campaign_goal="conversion",
    )

    prompt = build_kling_prompt(spec)

    assert "Student opens laptop" in prompt
    assert "handheld" in prompt
    assert "Bright home study area" in prompt
    assert len(prompt.split()) >= 40  # at least ~40 words
    assert len(prompt.split()) <= 200  # not excessively long


def test_build_kling_prompt_includes_brand_safety():
    from generate_video.video_spec import VideoSpec, build_kling_prompt
    spec = VideoSpec(
        scene="Simple scene",
        visual_style="realistic",
        camera_movement="static",
        subject_action="Person sitting",
        setting="Office",
        lighting_mood="Neutral",
        audio_mode="silent",
        audio_detail="",
        color_palette="",
        negative_prompt="",
        duration=5,
        aspect_ratio="1:1",
        text_overlay_sequence=[],
        persona="auto",
        campaign_goal="awareness",
    )

    prompt = build_kling_prompt(spec)

    assert "generic" in prompt.lower() or "no branded" in prompt.lower() or "unbranded" in prompt.lower()


def test_build_kling_prompt_excludes_negative_prompt_field():
    """The negative_prompt field value is NOT echoed into the prompt text —
    it goes as a separate Kling API parameter."""
    from generate_video.video_spec import VideoSpec, build_kling_prompt
    spec = VideoSpec(
        scene="Test", visual_style="realistic", camera_movement="static",
        subject_action="Standing", setting="Room", lighting_mood="Bright",
        audio_mode="silent", audio_detail="", color_palette="",
        negative_prompt="blur, distort, ugly artifacts, low resolution",
        duration=5, aspect_ratio="1:1", text_overlay_sequence=[],
        persona="auto", campaign_goal="awareness",
    )

    prompt = build_kling_prompt(spec)

    assert "blur" not in prompt
    assert "ugly artifacts" not in prompt
    assert "low resolution" not in prompt


# --- Brand safety negative prompt ---


def test_brand_safety_negative_prompt_always_present():
    """Even if user leaves negative_prompt empty, brand safety defaults apply."""
    from generate_video.video_spec import build_video_spec, BRAND_SAFETY_NEGATIVE

    config = _make_config(video_negative_prompt="")
    brief = _make_brief()
    copy = _make_copy()

    # Use explicit fields to avoid Gemini call
    config["video_scene"] = "Test scene"
    config["video_visual_style"] = "realistic"
    config["video_camera_movement"] = "static"
    config["video_subject_action"] = "Person standing"
    config["video_setting"] = "Room"
    config["video_lighting_mood"] = "Bright"

    spec = build_video_spec(brief, config, copy)

    assert BRAND_SAFETY_NEGATIVE in spec.negative_prompt
