"""
Output ActionPlan Model representing grounded, persona-specific emergency guidance.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.factsheet import FactSheet
from app.core.grade import GradeEngine
from app.core.rule_engine import rule_engine


@dataclass
class ActionPlan:
    """
    Immutable action intelligence output object combining threat grade, headline facts,
    ordered persona actions, and fact attribution IDs ('why').
    """
    grade: str
    persona: str
    hazard: str
    headline_facts: List[str]
    ordered_actions: List[Dict[str, Any]]
    why: List[str]
    expiry_time: Optional[str] = None
    safety_check_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grade": self.grade,
            "persona": self.persona,
            "hazard": self.hazard,
            "headline_facts": self.headline_facts,
            "ordered_actions": self.ordered_actions,
            "why": self.why,
            "expiry_time": self.expiry_time,
            "safety_check_required": self.safety_check_required,
        }


def generate_action_plan(
    factsheet: FactSheet,
    persona: str = "general",
    hazard_override: Optional[str] = None
) -> ActionPlan:
    """
    Generate an ActionPlan for a given FactSheet and persona without LLM dependency.
    """
    event_val = str(factsheet.get_value("event", "cyclone")).lower()
    if hazard_override:
        hazard = hazard_override
    elif "rain" in event_val or "flood" in event_val:
        hazard = "heavy_rain_flood"
    elif "heat" in event_val:
        hazard = "heatwave"
    elif "thunder" in event_val or "lightning" in event_val:
        hazard = "thunderstorm_lightning"
    elif "wave" in event_val or "surge" in event_val or "sea" in event_val:
        hazard = "storm_surge_high_waves"
    else:
        hazard = "cyclone"

    severity = factsheet.get_value("severity", "Moderate")
    urgency = factsheet.get_value("urgency", "Expected")
    certainty = factsheet.get_value("certainty", "Observed")

    grade_result = GradeEngine.evaluate(severity=severity, urgency=urgency, certainty=certainty)

    ordered_actions, why_fact_ids = rule_engine.get_actions(
        hazard=hazard,
        grade=grade_result.grade,
        persona=persona,
        factsheet=factsheet
    )

    headline_facts: List[str] = []
    for f in factsheet.facts[:5]:
        headline_facts.append(f"{f.id}: {f.field} = {f.value}")

    expiry_time = factsheet.get_value("expires")

    return ActionPlan(
        grade=grade_result.grade,
        persona=persona,
        hazard=hazard,
        headline_facts=headline_facts,
        ordered_actions=ordered_actions,
        why=why_fact_ids,
        expiry_time=expiry_time,
        safety_check_required=grade_result.requires_safety_check,
    )
