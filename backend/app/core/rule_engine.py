"""
Declarative YAML Rule Engine evaluating grounded actions per (hazard, grade, persona).
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.core.factsheet import FactSheet

logger = logging.getLogger("app.core.rules")


def normalize_hazard(hazard: str) -> str:
    """Normalize hazard string to YAML rule filename key."""
    h = hazard.lower().strip()
    h = re_sub_hazard(h)
    return h


def re_sub_hazard(h: str) -> str:
    canonical = {"heavy_rain_flood", "thunderstorm_lightning", "storm_surge_high_waves", "cyclone", "heatwave"}
    if h in canonical:
        return h
    if "heavy rain" in h or "flood" in h:
        return "heavy_rain_flood"
    if "thunderstorm" in h or "lightning" in h:
        return "thunderstorm_lightning"
    if "surge" in h or "wave" in h:
        return "storm_surge_high_waves"
    h = h.replace(" ", "_")
    return h


class RuleEngine:
    """
    Evaluates declarative YAML persona rules against a grounded FactSheet.
    """

    def __init__(self, rules_dir: Optional[str] = None) -> None:
        if rules_dir:
            self.rules_dir = Path(rules_dir)
        else:
            self.rules_dir = Path(__file__).resolve().parent / "rules"
        self._rules_cache: Dict[str, Dict[str, Any]] = {}

    def _load_hazard_rules(self, hazard: str) -> Dict[str, Any]:
        """Load and cache YAML rule file for normalized hazard."""
        norm_hazard = normalize_hazard(hazard)
        if norm_hazard in self._rules_cache:
            return self._rules_cache[norm_hazard]

        yaml_file = self.rules_dir / f"{norm_hazard}.yaml"
        if not yaml_file.exists():
            logger.warning(f"Rule file not found for hazard '{norm_hazard}' at {yaml_file}. Falling back to cyclone.")
            yaml_file = self.rules_dir / "cyclone.yaml"

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._rules_cache[norm_hazard] = data or {}
                return self._rules_cache[norm_hazard]
        except Exception as exc:
            logger.error(f"Failed to load YAML rule file {yaml_file}: {exc}")
            return {}

    def evaluate_fisherman_threshold(self, factsheet: FactSheet) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluate Fisherman threshold:
        - Wave height >= 2.5 meters OR Wind speed >= 45 km/h -> UNSAFE
        - Otherwise -> SAFE
        Returns (is_unsafe, wave_fact_id, wind_fact_id).
        """
        wave_fact = factsheet.get_fact("wave_height_m")
        wind_fact = factsheet.get_fact("wind_speed_kmh") or factsheet.get_fact("wind_gust_kmh")

        wave_val = float(wave_fact.value) if wave_fact and isinstance(wave_fact.value, (int, float)) else 0.0
        wind_val = float(wind_fact.value) if wind_fact and isinstance(wind_fact.value, (int, float)) else 0.0

        is_unsafe = (wave_val >= 2.5) or (wind_val >= 45.0)

        wave_id = wave_fact.id if wave_fact else None
        wind_id = wind_fact.id if wind_fact else None

        return is_unsafe, wave_id, wind_id

    def get_actions(
        self,
        hazard: str,
        grade: str,
        persona: str,
        factsheet: FactSheet
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Retrieve and format 2 to 4 grounded imperative actions for (hazard, grade, persona).
        Returns (rendered_actions, fact_ids_used).
        """
        norm_hazard = normalize_hazard(hazard)
        norm_persona = persona.lower().strip()
        norm_grade = grade.upper().strip()

        data = self._load_hazard_rules(norm_hazard)
        rules_list = data.get("rules", [])

        target_actions: List[Dict[str, Any]] = []
        for r in rules_list:
            if r.get("grade") == norm_grade and r.get("persona") == norm_persona:
                target_actions = r.get("actions", [])
                break

        # Fallback to general persona if specific persona rule missing
        if not target_actions:
            for r in rules_list:
                if r.get("grade") == norm_grade and r.get("persona") == "general":
                    target_actions = r.get("actions", [])
                    break

        rendered_actions: List[Dict[str, Any]] = []
        fact_ids_used: List[str] = []

        # Fisherman SAFE/UNSAFE status override check
        if norm_persona == "fisherman":
            is_unsafe, wave_fid, wind_fid = self.evaluate_fisherman_threshold(factsheet)
            if wave_fid:
                fact_ids_used.append(wave_fid)
            if wind_fid:
                fact_ids_used.append(wind_fid)

        for act in target_actions:
            act_id = act.get("id", "ACT-000")
            template = act.get("template", "")

            # Render template with FactSheet values
            rendered_text = template
            fact_fields = act.get("fact_fields", [])

            for f_field in fact_fields:
                fact_obj = factsheet.get_fact(f_field)
                val_str = ""
                if fact_obj is not None:
                    val_str = str(fact_obj.value)
                    if fact_obj.id not in fact_ids_used:
                        fact_ids_used.append(fact_obj.id)
                else:
                    val_str = "reported" if f_field in ("area", "onset") else "forecast"

                placeholder = f"{{{f_field}}}"
                rendered_text = rendered_text.replace(placeholder, val_str)

            if "{area}" in rendered_text:
                area_fact = factsheet.get_fact("area")
                area_val = str(area_fact.value) if area_fact else "Affected Area"
                rendered_text = rendered_text.replace("{area}", area_val)
                if area_fact and area_fact.id not in fact_ids_used:
                    fact_ids_used.append(area_fact.id)

            rendered_actions.append({
                "id": act_id,
                "action": rendered_text,
                "fact_refs": [f.id for f in factsheet.facts if f.field in fact_fields]
            })

        if not rendered_actions:
            area_fact = factsheet.get_fact("area")
            area_str = str(area_fact.value) if area_fact else "Affected Zone"
            rendered_actions = [
                {"id": f"ACT-{norm_hazard[:3].upper()}-{norm_grade}-01", "action": f"Stay indoors and monitor official weather bulletins for {area_str}.", "fact_refs": []},
                {"id": f"ACT-{norm_hazard[:3].upper()}-{norm_grade}-02", "action": "Keep mobile phone charged and emergency contact numbers accessible.", "fact_refs": []}
            ]

        deduped_fact_ids = list(dict.fromkeys(fact_ids_used))

        return rendered_actions, deduped_fact_ids


# Singleton instance
rule_engine = RuleEngine()
