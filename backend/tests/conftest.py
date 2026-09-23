import os

import pytest


@pytest.fixture(autouse=True)
def mock_llm_provider():
    """Ensure tests always use the deterministic TemplateClient to avoid network/API calls."""
    os.environ["LLM_PROVIDER"] = "template"
