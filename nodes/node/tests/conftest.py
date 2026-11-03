import pytest


@pytest.fixture(autouse=True)
def tls_desactive_par_defaut(monkeypatch):
    monkeypatch.setenv("TLS_ENABLED", "false")