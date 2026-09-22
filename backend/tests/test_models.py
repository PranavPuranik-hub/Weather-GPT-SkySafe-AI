from skysafe.models import Alert


def test_alert_model():
    alert = Alert(
        alert_id="TEST-001",
        headline="Heavy Rainfall Warning",
        severity="Severe",
        district="Cuttack"
    )
    assert alert.alert_id == "TEST-001"
    assert alert.district == "Cuttack"
