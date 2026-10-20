from datetime import datetime, timedelta, timezone

import jwt
import pytest


RUTAS = [
    ("POST", "/recursos/bloquear"),
    ("GET", "/recursos/disponibilidad"),
    ("POST", "/validaciones/evaluar-ofertas"),
]
SECRETO = "secreto-exclusivo-de-pruebas-locales-123456"
CREDENCIALES = {"usuario": "persona@example.org", "password": "clave-de-prueba"}


def instantanea_base(cliente):
    with cliente.app.state.sesiones() as sesion:
        conexion = sesion.connection().connection.driver_connection
        return tuple(conexion.iterdump())


@pytest.mark.parametrize("metodo,ruta", RUTAS)
def test_ruta_base_exige_token_valido_sin_modificar_datos(cliente, metodo, ruta):
    assert cliente.post("/auth/registro", json=CREDENCIALES).status_code == 201
    respuesta_login = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta_login.status_code == 200
    token = respuesta_login.json()["access_token"]
    estado_inicial = instantanea_base(cliente)

    respuesta = cliente.request(metodo, ruta, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json() == "Pendiente de implementación"
    assert instantanea_base(cliente) == estado_inicial

    datos = jwt.decode(
        token, SECRETO, algorithms=["HS256"],
        issuer="rescuesync-cloud", audience="rescuesync-cloud",
    )
    cabecera, contenido, firma = token.split(".")
    firma_alterada = ("A" if firma[0] != "A" else "B") + firma[1:]
    tokens_invalidos = [
        "basura",
        f"{cabecera}.{contenido}.{firma_alterada}",
        jwt.encode({**datos, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                   SECRETO, algorithm="HS256"),
        jwt.encode({**datos, "aud": "otra-api"}, SECRETO, algorithm="HS256"),
        jwt.encode({**datos, "iss": "otro-emisor"}, SECRETO, algorithm="HS256"),
    ]
    cabeceras_invalidas = [{}] + [
        {"Authorization": f"Bearer {invalido}"} for invalido in tokens_invalidos
    ]
    for cabeceras in cabeceras_invalidas:
        rechazo = cliente.request(metodo, ruta, headers=cabeceras)
        assert rechazo.status_code == 401
        assert rechazo.headers["www-authenticate"] == "Bearer"
        assert rechazo.json() == {"detail": "Credenciales inválidas"}
        assert instantanea_base(cliente) == estado_inicial


@pytest.mark.parametrize("metodo,ruta", RUTAS)
def test_openapi_declara_bearer_sin_cuerpo_ni_parametros(cliente, metodo, ruta):
    esquema = cliente.get("/openapi.json").json()
    operacion = esquema["paths"][ruta][metodo.lower()]
    assert operacion["security"] == [{"HTTPBearer": []}]
    assert "requestBody" not in operacion
    assert not operacion.get("parameters")
    assert operacion["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "string"
    assert esquema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http", "scheme": "bearer",
    }
