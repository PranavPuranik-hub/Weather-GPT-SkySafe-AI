"""
Immutable FactSheet Builder for Weather Alert Grounding.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass(frozen=True)
class Fact:
    """
    Single immutable grounded fact with a stable ID, source attribution, and text span reference.
    """
    id: str
    field: str
    value: Any
    source: str
    source_ref: Optional[str] = None
    source_span: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "source_ref": self.source_ref,
            "source_span": list(self.source_span) if self.source_span else None,
        }


@dataclass
class FactSheet:
    """
    Collection of immutable facts providing single-source-of-truth grounding for action plans.
    """
    facts: List[Fact] = field(default_factory=list)

    def get_fact(self, field_name: str) -> Optional[Fact]:
        """Return the first fact matching field_name."""
        for f in self.facts:
            if f.field == field_name:
                return f
        return None

    def get_value(self, field_name: str, default: Any = None) -> Any:
        """Return value of the matching field, or default if missing."""
        fact = self.get_fact(field_name)
        return fact.value if fact is not None else default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts]
        }


def _extract_text_facts(text: str, source_label: str, source_ref: Optional[str]) -> List[Dict[str, Any]]:
    """
    Use regex to extract numbers, units, and source character spans from free-text descriptions.
    """
    extracted: List[Dict[str, Any]] = []
    if not text:
        return extracted

    # 1. Wind speed / gusts (e.g. "95 km/h", "120-140 kmph", "gusts of 155 kmh")
    wind_pattern = re.compile(r'(?:wind|gusts?|speed)?\s*(?:of|up to|reaching)?\s*(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(\d+(?:\.\d+)?)?\s*(kmh|km/h|kmph|knots)', re.IGNORECASE)
    for match in wind_pattern.finditer(text):
        val1 = float(match.group(1))
        val2 = float(match.group(2)) if match.group(2) else val1
        max_val = max(val1, val2)
        unit = match.group(3).lower()
        # Convert knots to km/h if needed
        if "knot" in unit:
            max_val = round(max_val * 1.852, 1)

        is_gust = "gust" in match.group(0).lower()
        field_name = "wind_gust_kmh" if is_gust else "wind_speed_kmh"
        
        extracted.append({
            "field": field_name,
            "value": max_val,
            "source": source_label,
            "source_ref": source_ref,
            "source_span": (match.start(), match.end())
        })

    # 2. Wave height (e.g. "3.5 to 5.2 meters", "waves of 4.0 m")
    wave_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(\d+(?:\.\d+)?)?\s*(?:m|meters|metres)\s*(?:high|wave|swell)?', re.IGNORECASE)
    for match in wave_pattern.finditer(text):
        # Ignore if part of rainfall mm or kmh context
        context_window = text[max(0, match.start()-10):min(len(text), match.end()+10)].lower()
        if "mm" in context_window or "km" in context_window or "°" in context_window:
            continue
        val1 = float(match.group(1))
        val2 = float(match.group(2)) if match.group(2) else val1
        max_val = max(val1, val2)
        extracted.append({
            "field": "wave_height_m",
            "value": max_val,
            "source": source_label,
            "source_ref": source_ref,
            "source_span": (match.start(), match.end())
        })

    # 3. Rainfall depth (e.g. "204 mm", "15 cm")
    rain_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(mm|cm)\b', re.IGNORECASE)
    for match in rain_pattern.finditer(text):
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "cm":
            val = val * 10.0
        extracted.append({
            "field": "rainfall_mm",
            "value": val,
            "source": source_label,
            "source_ref": source_ref,
            "source_span": (match.start(), match.end())
        })

    # 4. Temperature (e.g. "47 °C", "45 deg C", "47C")
    temp_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:°C|deg C|degrees C|C\b)', re.IGNORECASE)
    for match in temp_pattern.finditer(text):
        val = float(match.group(1))
        # Ignore year numbers e.g. 2026C
        if val > 60.0 or val < -30.0:
            continue
        extracted.append({
            "field": "temperature_c",
            "value": val,
            "source": source_label,
            "source_ref": source_ref,
            "source_span": (match.start(), match.end())
        })

    return extracted


def build_factsheet(
    alert: Union[Dict[str, Any], Any],
    open_meteo_data: Optional[Dict[str, Any]] = None,
    ward_village: Optional[str] = None
) -> FactSheet:
    """
    Construct an immutable FactSheet from official alert metadata, free-text regex extraction,
    and Open-Meteo weather inputs.
    """
    raw_facts: List[Dict[str, Any]] = []

    # Helper function to get attr/item
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    alert_id = _get(alert, "identifier") or _get(alert, "alert_id") or "UNKNOWN-ALERT"
    source_ref = str(alert_id)

    # 1. Base CAP Metadata Facts
    event = _get(alert, "event") or _get(alert, "headline") or "Weather Alert"
    severity = _get(alert, "severity") or "Moderate"
    urgency = _get(alert, "urgency") or "Expected"
    certainty = _get(alert, "certainty") or "Observed"
    
    district = _get(alert, "district")
    state = _get(alert, "state")
    area_desc = _get(alert, "area_desc") or f"{district or ''}, {state or ''}".strip(", ")
    
    area_name = ward_village or area_desc or district or "Affected Zone"

    raw_facts.append({"field": "event", "value": str(event), "source": "CAP Alert info.event", "source_ref": source_ref})
    raw_facts.append({"field": "severity", "value": str(severity), "source": "CAP Alert info.severity", "source_ref": source_ref})
    raw_facts.append({"field": "urgency", "value": str(urgency), "source": "CAP Alert info.urgency", "source_ref": source_ref})
    raw_facts.append({"field": "certainty", "value": str(certainty), "source": "CAP Alert info.certainty", "source_ref": source_ref})
    raw_facts.append({"field": "area", "value": str(area_name), "source": "CAP Alert info.area", "source_ref": source_ref})

    onset = _get(alert, "onset") or _get(alert, "sent") or _get(alert, "effective")
    if onset:
        onset_str = onset.isoformat() if isinstance(onset, datetime) else str(onset)
        raw_facts.append({"field": "onset", "value": onset_str, "source": "CAP Alert info.onset", "source_ref": source_ref})

    expires = _get(alert, "expires")
    if expires:
        expires_str = expires.isoformat() if isinstance(expires, datetime) else str(expires)
        raw_facts.append({"field": "expires", "value": expires_str, "source": "CAP Alert info.expires", "source_ref": source_ref})

    # 2. Extract facts via regex from free-text fields
    headline = _get(alert, "headline") or ""
    description = _get(alert, "description") or ""
    instruction = _get(alert, "instruction") or ""

    if headline:
        raw_facts.extend(_extract_text_facts(headline, "IMD CAP info.headline", source_ref))
    if description:
        raw_facts.extend(_extract_text_facts(description, "IMD CAP info.description", source_ref))
    if instruction:
        raw_facts.extend(_extract_text_facts(instruction, "IMD CAP info.instruction", source_ref))

    # 3. Open-Meteo Data Facts
    if open_meteo_data:
        # Forecast
        hourly = open_meteo_data.get("hourly", {})
        if "wind_speed_10m" in hourly and hourly["wind_speed_10m"]:
            raw_facts.append({"field": "wind_speed_kmh", "value": max(hourly["wind_speed_10m"]), "source": "Open-Meteo Forecast", "source_ref": "hourly.wind_speed_10m"})
        if "wind_gusts_10m" in hourly and hourly["wind_gusts_10m"]:
            raw_facts.append({"field": "wind_gust_kmh", "value": max(hourly["wind_gusts_10m"]), "source": "Open-Meteo Forecast", "source_ref": "hourly.wind_gusts_10m"})
        if "precipitation" in hourly and hourly["precipitation"]:
            raw_facts.append({"field": "rainfall_mm", "value": sum(hourly["precipitation"]), "source": "Open-Meteo Forecast", "source_ref": "hourly.precipitation"})
        if "temperature_2m" in hourly and hourly["temperature_2m"]:
            raw_facts.append({"field": "temperature_c", "value": max(hourly["temperature_2m"]), "source": "Open-Meteo Forecast", "source_ref": "hourly.temperature_2m"})

        # Marine
        if "wave_height" in hourly and hourly["wave_height"]:
            raw_facts.append({"field": "wave_height_m", "value": max(hourly["wave_height"]), "source": "Open-Meteo Marine", "source_ref": "hourly.wave_height"})

        # Flood
        daily = open_meteo_data.get("daily", {})
        if "river_discharge" in daily and daily["river_discharge"]:
            raw_facts.append({"field": "river_discharge_m3s", "value": max(daily["river_discharge"]), "source": "Open-Meteo Flood", "source_ref": "daily.river_discharge"})

    # Build final list of Fact objects with sequential IDs F1, F2, F3...
    facts: List[Fact] = []
    seen_keys = set()
    fact_counter = 1

    for item in raw_facts:
        f_field = item["field"]
        f_val = item["value"]
        # Dedupe identical field+value pairs
        key = (f_field, str(f_val))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        fact_id = f"F{fact_counter}"
        fact_counter += 1

        facts.append(
            Fact(
                id=fact_id,
                field=f_field,
                value=f_val,
                source=item["source"],
                source_ref=item.get("source_ref"),
                source_span=item.get("source_span"),
            )
        )

    return FactSheet(facts=facts)
