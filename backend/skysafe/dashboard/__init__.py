"""
Dashboard package: Official decision matrix & district risk aggregation.
"""

def get_district_risk_summary(district: str) -> dict:
    """Return aggregated risk score and active alerts for district."""
    return {"district": district, "risk_level": "MODERATE", "alerts_count": 1}
