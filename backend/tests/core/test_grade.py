"""
Unit tests for GradeEngine threat grade evaluation.
"""
import pytest
from app.core.grade import GradeEngine, GradeResult


@pytest.mark.parametrize(
    "severity,urgency,certainty,color_code,expected_grade,expected_safety_check",
    [
        ("Extreme", "Immediate", "Observed", "Red", "A", True),
        ("Extreme", "Future", "Possible", None, "A", True),
        ("Severe", "Immediate", "Observed", "Orange", "A", True),
        ("Severe", "Expected", "Likely", "Orange", "B", False),
        ("Moderate", "Expected", "Observed", "Yellow", "C", False),
        ("Minor", "Past", "Unlikely", "Green", "D", False),
        ("Moderate", None, None, "Red", "A", True),
    ],
)
def test_grade_evaluation_matrix(
    severity, urgency, certainty, color_code, expected_grade, expected_safety_check
):
    result = GradeEngine.evaluate(
        severity=severity,
        urgency=urgency,
        certainty=certainty,
        color_code=color_code,
    )
    assert isinstance(result, GradeResult)
    assert result.grade == expected_grade
    assert result.requires_safety_check == expected_safety_check


def test_extreme_severity_mandatory_safety_check():
    result = GradeEngine.evaluate(severity="Extreme")
    assert result.grade == "A"
    assert result.requires_safety_check is True
    assert result.color_code == "Red"


def test_red_color_mandatory_safety_check():
    result = GradeEngine.evaluate(severity="Moderate", color_code="Red")
    assert result.grade == "A"
    assert result.requires_safety_check is True
    assert result.color_code == "Red"
