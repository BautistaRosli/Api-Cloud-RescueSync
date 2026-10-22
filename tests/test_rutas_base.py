from datetime import datetime, timedelta, timezone

import jwt
import pytest


RUTAS_PROTEGIDAS = [
    ("POST", "/recursos/bloquear"),
    ("GET", "/recursos/disponibilidad"),
    ("POST", "/validaciones/evaluar-ofertas"),
]
SECRETO = "secreto-exclusivo-de-pruebas-locales-123456"
CREDENCIALES = {"usuario": "integracion", "password": "clave-de-prueba"}
CUERPO_BLOQUEO = {
    "emergencia_id": 1,
    "ongs": [{"ong_id": 1, "items": [{"item_id": 1, "cantidad": 1}]}],
}


def instantanea_base(cliente):
    with cliente.app.state.sesiones() as sesion:
        conexion = sesion.connection().connection.driver_connection
        return tuple(conexion.iterdump())


def test_disponibilidad_no_modifica_datos(cliente):
    respuesta_login = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta_login.status_code == 200
    token = respuesta_login.json()["access_token"]
    estado_inicial = instantanea_base(cliente)

    respuesta = cliente.get("/recursos/disponibilidad", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert instantanea_base(cliente) == estado_inicial


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_ruta_rechaza_token_invalido_sin_modificar_datos(cliente, metodo, ruta):
    respuesta_login = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta_login.status_code == 200
    token = respuesta_login.json()["access_token"]
    estado_inicial = instantanea_base(cliente)
    cuerpo = CUERPO_BLOQUEO if ruta == "/recursos/bloquear" else None

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
        rechazo = cliente.request(metodo, ruta, headers=cabeceras, json=cuerpo)
        assert rechazo.status_code == 401
        assert rechazo.headers["www-authenticate"] == "Bearer"
        assert rechazo.json() == {"detail": "Credenciales inválidas"}
        assert instantanea_base(cliente) == estado_inicial


def test_openapi_declara_bearer_en_rutas_protegidas(cliente):
    esquema = cliente.get("/openapi.json").json()
    for metodo, ruta in RUTAS_PROTEGIDAS:
        assert esquema["paths"][ruta][metodo.lower()]["security"] == [{"HTTPBearer": []}]
    assert esquema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http", "scheme": "bearer",
    }


def test_openapi_bloquear_declara_cuerpo_y_respuesta(cliente):
    esquema = cliente.get("/openapi.json").json()
    operacion = esquema["paths"]["/recursos/bloquear"]["post"]
    assert "requestBody" in operacion
    assert operacion["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RespuestaBloqueo"
    )
