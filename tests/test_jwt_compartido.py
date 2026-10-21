from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import text

from app.config import cargar_configuracion


SECRETO = "secreto-exclusivo-de-pruebas-locales-123456"
CREDENCIALES = {"usuario": "integracion", "password": "clave-de-prueba"}
ONG = {"cuit": "30712345678", "razon_social": "ONG de prueba", "email": "ong@example.org"}


def obtener_identificador(cliente):
    with cliente.app.state.sesiones() as sesion:
        return sesion.execute(text("SELECT id FROM cuentas WHERE usuario = :usuario"),
                              {"usuario": CREDENCIALES["usuario"]}).scalar_one()


def claims_validos(identificador):
    ahora = datetime.now(timezone.utc)
    return {
        "sub": str(identificador), "usuario": CREDENCIALES["usuario"], "iss": "rescuesync-cloud",
        "aud": ["rescuesync-cloud", "rescuesync-backend"],
        "iat": ahora, "exp": ahora + timedelta(hours=1),
    }


def test_login_comparte_identidad_firmada_con_ambas_apis(cliente):
    identificador = obtener_identificador(cliente)
    respuesta = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta.status_code == 200
    for audiencia in ("rescuesync-cloud", "rescuesync-backend"):
        datos = jwt.decode(
            respuesta.json()["access_token"], SECRETO, algorithms=["HS256"],
            issuer="rescuesync-cloud", audience=audiencia,
            options={"require": ["sub", "usuario", "iat", "exp", "iss", "aud"]},
        )
        assert datos["sub"] == str(identificador)
        assert datos["usuario"] == CREDENCIALES["usuario"]
        assert datos["aud"] == ["rescuesync-cloud", "rescuesync-backend"]
        assert datos["exp"] - datos["iat"] == respuesta.json()["expires_in"]
        assert "rol" not in datos and "roles" not in datos


@pytest.mark.parametrize("campo", ["sub", "usuario", "iat", "exp", "iss", "aud"])
def test_guardia_exige_claims_incluso_en_tokens_anteriores(cliente, campo):
    identificador = obtener_identificador(cliente)
    datos = claims_validos(identificador)
    datos.pop(campo)
    comprobar_rechazo_sin_efectos(cliente, datos)


@pytest.mark.parametrize("cambios", [
    {"iss": "otro-emisor"},
    {"aud": ["rescuesync-backend"]},
    {"aud": "otra-api"},
    {"usuario": "otra-integracion"},
    {"usuario": 1},
    {"usuario": ""},
    {"sub": "999"},
    {"sub": "0"},
    {"sub": "invalido"},
    {"iat": datetime.now(timezone.utc) + timedelta(hours=1)},
])
def test_guardia_rechaza_identidad_o_destinatario_incorrectos(cliente, cambios):
    identificador = obtener_identificador(cliente)
    comprobar_rechazo_sin_efectos(cliente, {**claims_validos(identificador), **cambios})


def comprobar_rechazo_sin_efectos(cliente, datos):
    token = jwt.encode(datos, SECRETO, algorithm="HS256")
    respuesta = cliente.post("/ongs/registro", json=ONG, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert respuesta.json() == {"detail": "Credenciales inválidas"}
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM ongs")).scalar_one() == 0
        assert sesion.execute(text("SELECT count(*) FROM cuentas")).scalar_one() == 1


def test_guardia_acepta_audiencia_cloud_sin_asignar_roles(cliente):
    identificador = obtener_identificador(cliente)
    datos = {**claims_validos(identificador), "aud": "rescuesync-cloud", "roles": ["administrador"]}
    token = jwt.encode(datos, SECRETO, algorithm="HS256")
    respuesta = cliente.post("/ongs/registro", json=ONG, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 201
    assert respuesta.json() == {"id": 1, **ONG}


def test_configuracion_permite_emisor_y_destinatarios_explicitos(cliente, monkeypatch):
    monkeypatch.setenv("JWT_ISSUER", "emisor-integracion")
    monkeypatch.setenv("JWT_AUDIENCE", "cloud-integracion")
    monkeypatch.setenv("JWT_BACKEND_AUDIENCE", "backend-integracion")
    cliente.app.state.configuracion = cargar_configuracion()
    identificador = obtener_identificador(cliente)
    respuesta = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    for audiencia in ("cloud-integracion", "backend-integracion"):
        jwt.decode(token, SECRETO, algorithms=["HS256"], issuer="emisor-integracion", audience=audiencia)
    cabeceras = {"Authorization": f"Bearer {token}"}
    assert cliente.post("/ongs/registro", json=ONG, headers=cabeceras).status_code == 201
    comprobar_rechazo_sin_efectos_configurado(cliente, identificador)


def comprobar_rechazo_sin_efectos_configurado(cliente, identificador):
    token = jwt.encode(claims_validos(identificador), SECRETO, algorithm="HS256")
    respuesta = cliente.post("/ongs/registro", json={**ONG, "cuit": "30712345679"},
                             headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401
    with cliente.app.state.sesiones() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM ongs")).scalar_one() == 1
