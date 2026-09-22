"""
Unit tests for CLI demo execution.
"""
from app.core.demo import run_demo


def test_demo_scenarios_execution(capsys):
    for scenario in ["cyclone", "flood", "heatwave"]:
        run_demo(scenario)
        captured = capsys.readouterr()
        assert "SKYSAFE AI - DISASTER ACTION INTELLIGENCE CLI DEMO" in captured.out
        assert "Demo execution completed cleanly." in captured.out
