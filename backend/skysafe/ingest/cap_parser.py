"""
CAP 1.2 / 1.1 XML Alert Parser with Fault-Tolerant Geometry and Metadata Extraction.
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

logger = logging.getLogger("skysafe.ingest.cap")


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string with timezone awareness."""
    if not dt_str:
        return None
    cleaned = dt_str.strip()
    try:
        # datetime.fromisoformat handles +05:30 in Python 3.11
        return datetime.fromisoformat(cleaned)
    except Exception:
        # Fallback patterns
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(cleaned, fmt)
            except Exception:
                continue
    logger.warning(f"Could not parse datetime string: {dt_str}")
    return None


def _clean_tag(tag: str) -> str:
    """Strip XML namespace from tag name."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _extract_polygon_geojson(polygon_str: str | None) -> dict[str, Any] | None:
    """
    Convert CAP polygon string ("lat,lon lat,lon ...") to GeoJSON Polygon dict.
    GeoJSON coordinates format is [longitude, latitude].
    """
    if not polygon_str:
        return None
    pairs = polygon_str.strip().split()
    ring: list[list[float]] = []
    for pair in pairs:
        try:
            parts = pair.split(",")
            if len(parts) >= 2:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                ring.append([lon, lat])
        except (ValueError, IndexError):
            continue
    if len(ring) < 3:
        return None
    # Ensure closed ring
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return {
        "type": "Polygon",
        "coordinates": [ring]
    }


def parse_cap_xml(xml_content: str, source: str = "SACHET") -> dict[str, Any] | None:
    """
    Parse a CAP 1.2/1.1 XML string into a normalized dictionary.
    Returns None if XML is invalid or unparseable, ensuring ingestion resilience.
    """
    if not xml_content or not xml_content.strip():
        logger.warning("Empty CAP XML content provided.")
        return None

    try:
        root = ET.fromstring(xml_content)
    except Exception as exc:
        logger.warning(f"Failed to parse CAP XML: {exc}")
        return None

    root_tag = _clean_tag(root.tag)
    if root_tag != "alert":
        logger.warning(f"Root XML element is not 'alert', found: '{root_tag}'")
        return None

    # Map child elements by tag name without namespaces
    alert_map: dict[str, ET.Element] = {}
    for child in root:
        alert_map[_clean_tag(child.tag)] = child

    identifier = alert_map.get("identifier")
    identifier_val = identifier.text.strip() if identifier is not None and identifier.text else None
    if not identifier_val:
        logger.warning("CAP Alert missing required <identifier>")
        return None

    sender = alert_map.get("sender")
    sent = alert_map.get("sent")
    status = alert_map.get("status")
    msg_type = alert_map.get("msgType")
    scope = alert_map.get("scope")
    note = alert_map.get("note")

    status_val = status.text.strip() if status is not None and status.text else "Actual"
    note_val = note.text.strip() if note is not None and note.text else None
    is_simulation = (
        status_val.lower() == "exercise"
        or (note_val is not None and ("drill" in note_val.lower() or "simulated" in note_val.lower()))
    )

    # Info block (use first info if multiple exist)
    info_el = alert_map.get("info")
    info_map: dict[str, ET.Element] = {}
    if info_el is not None:
        for child in info_el:
            info_map[_clean_tag(child.tag)] = child

    language = info_map.get("language")
    category = info_map.get("category")
    event = info_map.get("event")
    urgency = info_map.get("urgency")
    severity = info_map.get("severity")
    certainty = info_map.get("certainty")
    effective = info_map.get("effective")
    onset = info_map.get("onset")
    expires = info_map.get("expires")
    headline = info_map.get("headline")
    description = info_map.get("description")
    instruction = info_map.get("instruction")

    # Area block
    area_el = info_map.get("area")
    area_desc_val: str | None = None
    polygon_val: str | None = None
    geocodes: list[dict[str, str]] = []

    if area_el is not None:
        for a_child in area_el:
            tag = _clean_tag(a_child.tag)
            if tag == "areaDesc" and a_child.text:
                area_desc_val = a_child.text.strip()
            elif tag == "polygon" and a_child.text:
                polygon_val = a_child.text.strip()
            elif tag == "geocode":
                v_name: str | None = None
                v_val: str | None = None
                for gc_child in a_child:
                    gc_tag = _clean_tag(gc_child.tag)
                    if gc_tag == "valueName" and gc_child.text:
                        v_name = gc_child.text.strip()
                    elif gc_tag == "value" and gc_child.text:
                        v_val = gc_child.text.strip()
                if v_name and v_val:
                    geocodes.append({"valueName": v_name, "value": v_val})

    # Location derivation (state and district)
    state_val: str | None = None
    district_val: str | None = None

    for gc in geocodes:
        vn = gc["valueName"].lower()
        if "state" in vn:
            state_val = gc["value"]
        elif "district" in vn:
            district_val = gc["value"]

    # Fallback parsing from areaDesc e.g. "Wayanad, Kerala" or "Cuttack, Odisha"
    if area_desc_val:
        if not district_val or not state_val:
            parts = [p.strip() for p in area_desc_val.split(",") if p.strip()]
            if len(parts) >= 2:
                if not district_val:
                    district_val = parts[0]
                if not state_val:
                    state_val = parts[1]
            elif len(parts) == 1 and not district_val:
                district_val = parts[0]

    if not district_val:
        district_val = "Unknown District"

    geojson_dict = _extract_polygon_geojson(polygon_val)
    geometry_json = json.dumps(geojson_dict) if geojson_dict else None

    # Compute sent and expires datetimes
    sent_dt = _parse_datetime(sent.text if sent is not None else None)
    effective_dt = _parse_datetime(effective.text if effective is not None else None)
    onset_dt = _parse_datetime(onset.text if onset is not None else None)
    expires_dt = _parse_datetime(expires.text if expires is not None else None)

    # Check expiration status
    now = datetime.now().astimezone() if sent_dt and sent_dt.tzinfo else datetime.utcnow()
    is_expired = False
    if expires_dt:
        # Compare naive or aware safely
        if expires_dt.tzinfo and now.tzinfo or not expires_dt.tzinfo and not now.tzinfo:
            is_expired = now > expires_dt

    return {
        "alert_id": identifier_val,
        "identifier": identifier_val,
        "sender": sender.text.strip() if sender is not None and sender.text else None,
        "sent": sent_dt,
        "status": status_val,
        "msg_type": msg_type.text.strip() if msg_type is not None and msg_type.text else "Alert",
        "scope": scope.text.strip() if scope is not None and scope.text else "Public",
        "note": note_val,
        "language": language.text.strip() if language is not None and language.text else "en",
        "category": category.text.strip() if category is not None and category.text else "Met",
        "event": event.text.strip() if event is not None and event.text else "Weather Alert",
        "urgency": urgency.text.strip() if urgency is not None and urgency.text else "Unknown",
        "severity": severity.text.strip() if severity is not None and severity.text else "Moderate",
        "certainty": certainty.text.strip() if certainty is not None and certainty.text else "Unknown",
        "effective": effective_dt,
        "onset": onset_dt,
        "expires": expires_dt,
        "headline": headline.text.strip() if headline is not None and headline.text else "Weather Warning",
        "description": description.text.strip() if description is not None and description.text else None,
        "instruction": instruction.text.strip() if instruction is not None and instruction.text else None,
        "area_desc": area_desc_val,
        "polygon": polygon_val,
        "geocode": json.dumps(geocodes) if geocodes else None,
        "geometry": geometry_json,
        "state": state_val,
        "district": district_val,
        "is_expired": is_expired,
        "is_simulation": is_simulation,
        "source": source,
        "raw_xml": xml_content,
    }
