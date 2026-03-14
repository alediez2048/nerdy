"""Tests for audience-specific brand voice profiles (P1-03).

TDD: Tests written first. Validates VoiceProfile, get_voice_for_prompt,
get_voice_for_evaluation, audience fallback.
"""

from __future__ import annotations


from generate.brand_voice import (
    VoiceProfile,
    get_voice_for_evaluation,
    get_voice_for_prompt,
    get_voice_profile,
)


# --- Audience Profiles ---


def test_parent_audience_returns_parent_facing_profile() -> None:
    """get_voice_profile('parents') returns parent-facing profile."""
    profile = get_voice_profile("parents")
    assert profile.audience in ("parents", "parent")
    assert "authoritative" in profile.tone or "reassuring" in profile.tone


def test_student_audience_returns_student_facing_profile() -> None:
    """get_voice_profile('students') returns student-facing profile."""
    profile = get_voice_profile("students")
    assert profile.audience in ("students", "student")
    assert "relatable" in profile.tone or "motivating" in profile.tone


def test_unknown_audience_falls_back_to_default() -> None:
    """Unknown audience returns default profile, does not crash."""
    profile = get_voice_profile("unknown_segment")
    assert isinstance(profile, VoiceProfile)
    assert profile.audience


def test_profile_contains_all_required_fields() -> None:
    """VoiceProfile has tone, emotional_drivers, vocabulary_guidance, few_shot_examples, anti_examples, brand_constants."""
    profile = get_voice_profile("parents")
    assert hasattr(profile, "tone")
    assert hasattr(profile, "emotional_drivers")
    assert hasattr(profile, "vocabulary_guidance")
    assert hasattr(profile, "few_shot_examples")
    assert hasattr(profile, "anti_examples")
    assert hasattr(profile, "brand_constants")
    assert isinstance(profile.tone, list)
    assert isinstance(profile.emotional_drivers, list)
    assert isinstance(profile.few_shot_examples, list)
    assert isinstance(profile.anti_examples, list)
    assert isinstance(profile.brand_constants, list)


def test_few_shot_examples_are_non_empty() -> None:
    """Few-shot examples list is non-empty for known audiences."""
    for audience in ("parents", "students"):
        profile = get_voice_profile(audience)
        assert len(profile.few_shot_examples) >= 1


def test_get_voice_for_prompt_returns_non_empty_string() -> None:
    """get_voice_for_prompt() produces prompt-injectable string."""
    for audience in ("parents", "students"):
        s = get_voice_for_prompt(audience)
        assert isinstance(s, str)
        assert len(s) > 50


def test_get_voice_for_evaluation_returns_non_empty_string() -> None:
    """get_voice_for_evaluation() produces evaluator rubric string."""
    for audience in ("parents", "students"):
        s = get_voice_for_evaluation(audience)
        assert isinstance(s, str)
        assert len(s) > 50


def test_brand_constants_present_in_all_profiles() -> None:
    """brand_constants (empowering, knowledgeable, etc.) appear in all profiles."""
    for audience in ("parents", "students", "families", "unknown"):
        profile = get_voice_profile(audience)
        assert len(profile.brand_constants) >= 1
        assert any("empowering" in str(c).lower() or "knowledgeable" in str(c).lower() for c in profile.brand_constants)


def test_parent_and_student_profiles_differ() -> None:
    """Parent and student profiles have different tone descriptors."""
    parent = get_voice_profile("parents")
    student = get_voice_profile("students")
    # At least one tone should differ
    assert set(parent.tone) != set(student.tone) or parent.emotional_drivers != student.emotional_drivers


def test_families_audience_returns_default_or_both_profile() -> None:
    """'families' audience returns a valid profile (default/family)."""
    profile = get_voice_profile("families")
    assert isinstance(profile, VoiceProfile)
    assert profile.audience
