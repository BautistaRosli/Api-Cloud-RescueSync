from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app


CREDENCIALES = {"usuario": "integracion", "password": "clave-de-prueba"}
ONG = {"cuit": "30712345678", "razon_social": "ONG de prueba", "email": "contacto@example.org"}


def autorizar(cliente):
    assert cliente.post("/auth/registro", json=CREDENCIALES).status_code == 201
    respuesta = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_registro_publico_persiste_hash_salteado(cliente):
    respuesta = cliente.post("/auth/registro", json=CREDENCIALES)
    assert respuesta.status_code == 201
    assert respuesta.json() == {"id": 1, "usuario": "integracion"}
    segunda = {**CREDENCIALES, "usuario": "otra-cuenta"}
    assert cliente.post("/auth/registro", json=segunda).status_code == 201
    with cliente.app.state.sesiones() as sesion:
        hashes = sesion.execute(text("SELECT password_hash FROM cuentas ORDER BY id")).scalars().all()
    assert len(hashes) == 2
    assert hashes[0] != hashes[1]
    assert all(CREDENCIALES["password"] not in valor for valor in hashes)


def test_login_emite_jwt_y_rechaza_credenciales_invalidas(cliente):
    cabeceras = autorizar(cliente)
    token = cabeceras["Authorization"].removeprefix("Bearer ")
    datos = jwt.decode(
        token, "secreto-exclusivo-de-pruebas-locales-123456", algorithms=["HS256"],
        issuer="rescuesync-cloud", audience="rescuesync-cloud",
    )
    assert datos["sub"] == "1"
    assert datos["exp"] > datos["iat"]
    respuesta = cliente.post("/auth/login", json=CREDENCIALES)
    assert set(respuesta.json()) == {"access_token", "token_type", "expires_in"}
    assert respuesta.json()["token_type"] == "bearer"
    assert respuesta.json()["expires_in"] > 0
    for datos_invalidos in [
        {**CREDENCIALES, "password": "incorrecta"},
        {**CREDENCIALES, "usuario": "desconocido"},
    ]:
        respuesta = cliente.post("/auth/login", json=datos_invalidos)
        assert respuesta.status_code == 401
        assert respuesta.headers["www-authenticate"] == "Bearer"
        assert "password" not in respuesta.text


def test_registro_duplicado_rechaza_y_permite_otro_registro(cliente):
    assert cliente.post("/auth/registro", json=CREDENCIALES).status_code == 201
    assert cliente.post("/auth/registro", json=CREDENCIALES).status_code == 409
    assert cliente.post("/auth/registro", json={**CREDENCIALES, "usuario": "otra"}).status_code == 201
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM cuentas")).scalar_one() == 2


@pytest.mark.parametrize("ruta", ["/auth/registro", "/auth/login"])
@pytest.mark.parametrize("datos", [
    {"usuario": "", "password": "secreto-no-reflejar"},
    {"usuario": "  ", "password": "secreto-no-reflejar"},
    {"usuario": "integracion"},
    {"password": "secreto-no-reflejar"},
    {"usuario": "integracion", "password": ""},
    {"usuario": "integracion", "password": None},
    {"usuario": "integracion", "password": "   "},
    {"usuario": "integracion", "password": {"secreto-no-reflejar": "valor"}},
    {"usuario": "integracion", "password": "secreto-no-reflejar", "extra": "secreto-no-reflejar"},
])
def test_validacion_auth_no_expone_credenciales(cliente, ruta, datos):
    respuesta = cliente.post(ruta, json=datos)
    assert respuesta.status_code == 422
    assert "secreto-no-reflejar" not in respuesta.text
    for error in respuesta.json()["detail"]:
        assert "input" not in error
        assert "ctx" not in error


def test_registro_ong_persiste_solo_campos_acordados(cliente):
    cabeceras = autorizar(cliente)
    respuesta = cliente.post("/ongs/registro", json=ONG, headers=cabeceras)
    assert respuesta.status_code == 201
    assert respuesta.json() == {"id": 1, **ONG}
    with cliente.app.state.sesiones() as sesion:
        datos = sesion.execute(text("SELECT cuit, razon_social, email FROM ongs")).mappings().one()
        assert dict(datos) == ONG


@pytest.mark.parametrize("campo", ["cuit", "razon_social", "email"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_campos_ong_obligatorios(cliente, campo, valor):
    cabeceras = autorizar(cliente)
    datos = dict(ONG)
    if valor is None:
        datos.pop(campo)
    else:
        datos[campo] = valor
    assert cliente.post("/ongs/registro", json=datos, headers=cabeceras).status_code == 422
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM ongs")).scalar_one() == 0


def test_email_ong_valido_y_sin_datos_adicionales(cliente):
    cabeceras = autorizar(cliente)
    for datos in [{**ONG, "email": "invalido"}, {**ONG, "telefono": "123"}]:
        assert cliente.post("/ongs/registro", json=datos, headers=cabeceras).status_code == 422


def test_cuit_duplicado_y_rollback(cliente):
    cabeceras = autorizar(cliente)
    assert cliente.post("/ongs/registro", json=ONG, headers=cabeceras).status_code == 201
    assert cliente.post("/ongs/registro", json=ONG, headers=cabeceras).status_code == 409
    otra = {**ONG, "cuit": "30712345679"}
    assert cliente.post("/ongs/registro", json=otra, headers=cabeceras).status_code == 201
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM ongs")).scalar_one() == 2


@pytest.mark.parametrize("tipo", ["ausente", "invalido", "expirado", "alterado", "algoritmo"])
def test_guardia_jwt_ong_no_persiste_sin_token_valido(cliente, tipo):
    cabeceras = autorizar(cliente)
    ahora = datetime.now(timezone.utc)
    if tipo == "ausente":
        cabeceras = {}
    elif tipo == "invalido":
        cabeceras = {"Authorization": "Bearer invalido"}
    elif tipo in {"expirado", "algoritmo"}:
        token = jwt.encode(
            {"sub": "1", "usuario": CREDENCIALES["usuario"], "iss": "rescuesync-cloud",
             "aud": ["rescuesync-cloud", "rescuesync-backend"], "iat": ahora - timedelta(hours=2),
             "exp": ahora - timedelta(hours=1) if tipo == "expirado" else ahora + timedelta(hours=1)},
            "secreto-exclusivo-de-pruebas-locales-123456",
            algorithm="HS256" if tipo == "expirado" else "HS384",
        )
        cabeceras = {"Authorization": f"Bearer {token}"}
    else:
        token = cabeceras["Authorization"].split()[1]
        cabecera, cuerpo, firma = token.split(".")
        firma = ("A" if firma[0] != "A" else "B") + firma[1:]
        cabeceras = {"Authorization": f"Bearer {cabecera}.{cuerpo}.{firma}"}
    respuesta = cliente.post("/ongs/registro", json=ONG, headers=cabeceras)
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM ongs")).scalar_one() == 0


def test_contratos_ejemplos_y_documentacion_publicos(cliente):
    assert cliente.get("/health").json() == {"status": "ok"}
    assert cliente.get("/docs").status_code == 200
    especificacion = cliente.get("/openapi.json").json()
    assert especificacion["paths"]["/ongs/registro"]["post"]["security"] == [{"HTTPBearer": []}]
    usuario = cliente.post("/users/", json={"name": "Ana", "email": "ana@example.org"})
    assert usuario.status_code == 200
    assert usuario.json() == {"id": 1, "name": "Ana", "email": "ana@example.org"}
    assert cliente.get("/users/").json() == [usuario.json()]
    assert cliente.get("/users/1").json() == usuario.json()
    assert cliente.get("/users/999").json() == {"detail": "User not found"}
    item = cliente.post("/items/", json={"name": "Agua", "owner_id": 1})
    assert item.status_code == 200
    assert item.json() == {"id": 1, "name": "Agua", "description": None, "owner_id": 1}
    assert cliente.get("/items/").json() == [item.json()]
    assert cliente.get("/items/1").json() == item.json()
    assert cliente.delete("/items/1").json() == {"detail": "Item deleted"}
    assert cliente.get("/items/1").status_code == 404


def test_documentacion_y_salud_sin_configuracion(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with TestClient(app) as cliente:
        assert cliente.get("/docs").status_code == 200
        assert cliente.get("/openapi.json").status_code == 200
        assert cliente.get("/health").json() == {"status": "ok"}
        assert cliente.post("/auth/registro", json=CREDENCIALES).status_code == 503
        assert cliente.post("/auth/login", json=CREDENCIALES).status_code == 503
        assert cliente.post("/ongs/registro", json=ONG).status_code == 503
