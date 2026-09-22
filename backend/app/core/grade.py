"""
Deterministic Grade Engine Mapping Severity, Urgency, Certainty, and Color Codes to Action Grades.
"""
from dataclasses import dataclass
from typing import Literal, Optional


GradeType = Literal["A", "B", "C", "D"]
ColorCodeType = Literal["Red", "Orange", "Yellow", "Green"]


@dataclass(frozen=True)
class GradeResult:
    """
    Evaluated threat grade result with mandatory safety check flag.
    """
    grade: GradeType
    reason: str
    color_code: ColorCodeType
    requires_safety_check: bool


class GradeEngine:
    """
    Deterministic rule engine mapping weather hazard attributes to Grades:
    - Grade A: Act Now / Evacuate
    - Grade B: Prepare to Act
    - Grade C: Stay Alert
    - Grade D: Information Only
    """

    @staticmethod
    def evaluate(
        severity: str,
        urgency: Optional[str] = None,
        certainty: Optional[str] = None,
        color_code: Optional[str] = None,
    ) -> GradeResult:
        """
        Evaluate inputs against the documented grade mapping matrix.
        Enforces Rule: If severity is Extreme or color is Red -> Grade A + Safety Check for all recipients.
        """
        sev = (severity or "Moderate").strip().title()
        urg = (urgency or "Expected").strip().title()
        cert = (certainty or "Observed").strip().title()
        color = (color_code or "").strip().title()

        # Resolve IMD Color Code if not explicitly provided
        if not color:
            if sev == "Extreme":
                color = "Red"
            elif sev == "Severe":
                color = "Orange"
            elif sev == "Moderate":
                color = "Yellow"
            else:
                color = "Green"

        # Mandatory Safety Check Rule (Extreme severity or Red alert)
        if sev == "Extreme" or color == "Red":
            return GradeResult(
                grade="A",
                reason="Extreme threat to life and property / Red Warning issued.",
                color_code="Red",
                requires_safety_check=True,
            )

        # Grade A: Severe + Immediate
        if sev == "Severe" and urg == "Immediate":
            return GradeResult(
                grade="A",
                reason="Severe threat with immediate onset.",
                color_code=color if color in ("Red", "Orange", "Yellow", "Green") else "Orange",
                requires_safety_check=True,
            )

        # Grade B: Severe / Orange Alert / Expected Immediate
        if color == "Orange" or sev == "Severe" or (urg == "Immediate" and sev in ("Moderate", "Severe")):
            return GradeResult(
                grade="B",
                reason="High probability of severe weather impact; prepare to act.",
                color_code="Orange",
                requires_safety_check=False,
            )

        # Grade C: Moderate / Yellow Alert
        if color == "Yellow" or sev == "Moderate":
            return GradeResult(
                grade="C",
                reason="Moderate weather disturbance expected; stay alert.",
                color_code="Yellow",
                requires_safety_check=False,
            )

        # Grade D: Minor / Green / Information Only
        return GradeResult(
            grade="D",
            reason="Low severity advisory; information only.",
            color_code="Green",
            requires_safety_check=False,
        )
