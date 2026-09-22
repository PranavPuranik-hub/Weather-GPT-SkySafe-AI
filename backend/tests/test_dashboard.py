from app.dashboard import get_district_risk_summary


def test_district_risk_summary():
    summary = get_district_risk_summary("Cuttack")
    assert summary["district"] == "Cuttack"
    assert "risk_level" in summary
