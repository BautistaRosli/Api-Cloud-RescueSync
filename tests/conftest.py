import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import items, users
from app.services.auth_service import generar_hash


@pytest.fixture(scope="session")
def cuenta_semilla():
    password = "clave-de-prueba"
    return {
        "usuario": "integracion",
        "password": password,
        "password_hash": generar_hash(password),
    }


@pytest.fixture
def cliente(tmp_path, monkeypatch, cuenta_semilla):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cloud.db'}")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-de-pruebas-locales-123456")
    monkeypatch.setenv("USUARIO_RESCUESYNC", cuenta_semilla["usuario"])
    monkeypatch.setenv("PASSWORD_RESCUESYNC", cuenta_semilla["password"])
    for variable in ("JWT_ISSUER", "JWT_AUDIENCE", "JWT_BACKEND_AUDIENCE"):
        monkeypatch.delenv(variable, raising=False)
    users.fake_db.clear()
    users.counter = 0
    items.fake_db.clear()
    items.counter = 0
    with TestClient(app) as cliente:
        yield cliente
