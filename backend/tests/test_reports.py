from skysafe.reports import generate_sitrep


def test_generate_sitrep():
    report = generate_sitrep("Cuttack")
    assert "Situation Report" in report
    assert "Cuttack" in report
    assert "DRILL / SIMULATION" in report
