# PB-03: Nerdy language compliance tests
"""Tests for Nerdy-specific do's/don'ts, fake urgency, corporate jargon, and competitor handling."""

from generate.compliance import check_compliance, check_nerdy_positives


# --- Critical violations ---


def test_your_student_is_critical():
    result = check_compliance("Help your student ace the SAT")
    assert not result.passes
    assert result.has_critical
    crits = [v for v in result.violations if v.rule_name == "nerdy_wrong_address"]
    assert len(crits) == 1
    assert crits[0].severity == "critical"


def test_sat_prep_is_critical():
    result = check_compliance("Best SAT Prep in the country")
    assert not result.passes
    crits = [v for v in result.violations if v.rule_name == "nerdy_wrong_product"]
    assert len(crits) == 1


def test_spots_filling_fast_is_critical():
    result = check_compliance("Spots filling fast — enroll today!")
    assert not result.passes
    assert any(v.rule_name == "fake_urgency" for v in result.violations)


def test_limited_enrollment_is_critical():
    result = check_compliance("Limited enrollment available for spring")
    assert not result.passes
    assert any(v.rule_name == "fake_urgency" for v in result.violations)


def test_dont_miss_out_is_critical():
    result = check_compliance("Don't miss out on this opportunity")
    assert not result.passes
    assert any(v.rule_name == "fake_urgency" for v in result.violations)


def test_secure_their_spot_is_critical():
    result = check_compliance("Secure their spot before it's too late")
    assert not result.passes
    assert any(v.rule_name == "fake_urgency" for v in result.violations)


def test_online_tutoring_is_critical():
    result = check_compliance("Try our online tutoring platform")
    assert not result.passes
    assert any(v.rule_name == "online_tutoring_frame" for v in result.violations)


def test_score_guarantee_specific_is_critical():
    result = check_compliance("Guaranteed 1500+ or your money back")
    assert not result.passes
    assert any(v.rule_name in ("guaranteed_outcome", "score_guarantee") for v in result.violations)


# --- Warnings (flag but don't block) ---


def test_unlock_potential_is_warning():
    result = check_compliance("Unlock their potential with our program")
    assert result.passes  # warnings don't block
    warnings = result.warnings
    assert any(v.rule_name == "corporate_jargon" for v in warnings)


def test_maximize_score_is_warning():
    result = check_compliance("Maximize score potential this semester")
    assert result.passes
    assert any(v.rule_name == "corporate_jargon" for v in result.warnings)


def test_tailored_support_is_warning():
    result = check_compliance("We offer tailored support for every learner")
    assert result.passes
    assert any(v.rule_name == "corporate_jargon" for v in result.warnings)


# --- Clean copy passes ---


def test_your_child_passes_clean():
    result = check_compliance("Help your child raise their SAT score with 1-on-1 tutoring")
    critical = result.critical_violations
    assert len(critical) == 0
    assert result.passes


def test_sat_tutoring_passes_clean():
    result = check_compliance("SAT Tutoring that actually raises scores")
    critical = result.critical_violations
    assert len(critical) == 0


def test_full_nerdy_approved_copy_passes():
    copy = (
        "3.8 GPA. 1260 SAT. Something's off. "
        "Most mid-1200s students are 3–4 targeted fixes away from a 1400+. "
        "Your child gets a dedicated SAT tutor who diagnoses exactly where points are hiding. "
        "See what score is realistic in 8–10 weeks."
    )
    result = check_compliance(copy)
    assert result.passes
    assert len(result.critical_violations) == 0


# --- Competitor comparisons with data are allowed ---


def test_competitor_with_real_data_is_info_not_critical():
    copy = "Princeton Review charges $252/hr for 1:1. We charge $349/month for the same thing."
    result = check_compliance(copy)
    # Should pass (no critical violations from competitor names)
    assert result.passes
    # Competitor names show up as "info" not "critical"
    comp_viols = [v for v in result.violations if v.rule_name == "competitor_reference"]
    assert len(comp_viols) >= 1
    assert all(v.severity == "info" for v in comp_viols)


# --- Positive validation ---


def test_nerdy_positives_detects_approved_patterns():
    copy = (
        "Your child can gain 200 points in 16 sessions with SAT Tutoring. "
        "The digital SAT interface has a built-in calculator that most students don't know how to use. "
        "Princeton Review charges $252/hr for 1:1."
    )
    positives = check_nerdy_positives(copy)
    assert "uses_your_child" in positives
    assert "uses_sat_tutoring" in positives
    assert "conditional_claim" in positives
    assert "specific_mechanism" in positives
    assert "competitor_comparison_with_data" in positives


def test_nerdy_positives_empty_for_generic_copy():
    copy = "Get better at the test. Sign up now."
    positives = check_nerdy_positives(copy)
    assert len(positives) == 0


# --- ComplianceResult properties ---


def test_has_critical_property():
    result = check_compliance("Your student needs SAT Prep")
    assert result.has_critical
    assert len(result.critical_violations) == 2  # your student + SAT Prep


def test_warnings_property():
    result = check_compliance("Unlock their potential with custom strategies")
    assert result.passes
    assert len(result.warnings) == 2  # unlock potential + custom strategies
