"""Keep tests isolated from developer credentials and external model APIs."""

import pytest


@pytest.fixture(autouse=True)
def disable_local_dotenv_loading(monkeypatch):
    """Tests must use explicit fake credentials and never read a developer .env."""
    import patchpilot.config

    monkeypatch.setattr(patchpilot.config, "load_dotenv", lambda: None)
