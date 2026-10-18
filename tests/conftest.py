import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import items, users


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cloud.db'}")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-de-pruebas-locales-123456")
    for variable in ("JWT_ISSUER", "JWT_AUDIENCE", "JWT_BACKEND_AUDIENCE"):
        monkeypatch.delenv(variable, raising=False)
    users.fake_db.clear()
    users.counter = 0
    items.fake_db.clear()
    items.counter = 0
    with TestClient(app) as cliente:
        yield cliente
