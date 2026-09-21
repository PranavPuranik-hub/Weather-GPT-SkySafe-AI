from skysafe.i18n import translate

def test_translation_function():
    result = translate("Stay indoors", lang="hi")
    assert isinstance(result, str)
    assert len(result) > 0
