from app.agent import NullProvider


def test_null_agent_provider():
    provider = NullProvider()
    response = provider.generate("Give action for cyclone alert")
    assert isinstance(response, str)
    assert len(response) > 0
