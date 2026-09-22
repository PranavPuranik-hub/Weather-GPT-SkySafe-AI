from app.grounding import validate_grounding


def test_grounding_validation():
    valid = validate_grounding("Seek shelter immediately.", {"district": "Cuttack"})
    assert valid is True
