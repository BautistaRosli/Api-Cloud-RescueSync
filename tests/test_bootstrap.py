import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Configuracion, cargar_configuracion
from dataclasses import replace
from app.models import Base, Cuenta, Ong
from app.services.auth_service import generar_hash


@pytest.fixture
def aplicacion(monkeypatch, cuenta_semilla):
    import app.main as principal

    motor = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    sesiones = sessionmaker(bind=motor, expire_on_commit=False)
    cerrar_motor = motor.dispose
    monkeypatch.setattr(motor, "dispose", lambda: None)

    def iniciar_base_prueba(database_url):
        assert database_url == "sqlite://"
        Base.metadata.create_all(motor)
        return motor, sesiones

    monkeypatch.setattr(principal, "iniciar_base_datos", iniciar_base_prueba)
    monkeypatch.setattr(
        principal, "cargar_configuracion",
        lambda: Configuracion(
            "sqlite://", "secreto-exclusivo-bootstrap-pruebas-123456",
            usuario_rescuesync=cuenta_semilla["usuario"],
            password_hash_rescuesync=cuenta_semilla["password_hash"],
        ),
    )
    yield principal.app, sesiones
    cerrar_motor()


def test_arranque_vacio_crea_solo_cuenta_rescuesync_con_hash(aplicacion, cuenta_semilla):
    app, sesiones = aplicacion
    with TestClient(app):
        with sesiones() as sesion:
            cuentas = sesion.scalars(select(Cuenta)).all()
            assert len(cuentas) == 1
            assert cuentas[0].usuario == cuenta_semilla["usuario"]
            assert cuentas[0].password_hash == cuenta_semilla["password_hash"]
            assert cuentas[0].password_hash.startswith("pbkdf2_sha256$600000$")
            assert sesion.scalars(select(Ong)).all() == []


def test_segundo_arranque_preserva_identidades_hashes_y_datos(aplicacion, monkeypatch):
    import app.main as principal

    app, sesiones = aplicacion
    with TestClient(app):
        with sesiones.begin() as sesion:
            sesion.add(Cuenta(usuario="otra-aplicacion", password_hash=generar_hash("clave-otra-prueba")))
            sesion.add(Ong(cuit="30712345678", razon_social="ONG existente", email="ong@example.org"))
        with sesiones() as sesion:
            cuentas_antes = [(c.id, c.usuario, c.password_hash) for c in sesion.scalars(select(Cuenta))]
            ongs_antes = [(o.id, o.cuit, o.razon_social, o.email) for o in sesion.scalars(select(Ong))]
            assert len(cuentas_antes) == 2

    configuracion_modificada = replace(
        app.state.configuracion, password_hash_rescuesync=generar_hash("otra-clave-semilla-ficticia"),
    )
    monkeypatch.setattr(principal, "cargar_configuracion", lambda: configuracion_modificada)
    with TestClient(app):
        with sesiones() as sesion:
            assert [(c.id, c.usuario, c.password_hash) for c in sesion.scalars(select(Cuenta))] == cuentas_antes
            assert [(o.id, o.cuit, o.razon_social, o.email) for o in sesion.scalars(select(Ong))] == ongs_antes


def test_arranque_no_reemplaza_hash_de_cuenta_existente(aplicacion, cuenta_semilla):

    app, sesiones = aplicacion
    Base.metadata.create_all(sesiones.kw["bind"])
    hash_existente = generar_hash("clave-existente-prueba")
    with sesiones.begin() as sesion:
        cuenta = Cuenta(usuario=cuenta_semilla["usuario"], password_hash=hash_existente)
        sesion.add(cuenta)
    with TestClient(app):
        with sesiones() as sesion:
            cuentas = sesion.scalars(select(Cuenta)).all()
            assert len(cuentas) == 1
            assert cuentas[0].id == cuenta.id
            assert cuentas[0].password_hash == hash_existente


def test_login_semilla_y_registro_publico_conservan_contratos(aplicacion, cuenta_semilla):

    app, sesiones = aplicacion
    password_prueba = cuenta_semilla["password"]
    with TestClient(app) as cliente:
        credenciales = {"usuario": cuenta_semilla["usuario"], "password": password_prueba}
        respuesta = cliente.post("/auth/login", json=credenciales)
        assert respuesta.status_code == 200
        assert set(respuesta.json()) == {"access_token", "token_type", "expires_in"}
        assert respuesta.json()["token_type"] == "bearer"
        assert password_prueba not in respuesta.text
        rechazo = cliente.post("/auth/login", json={**credenciales, "password": "incorrecta"})
        assert rechazo.status_code == 401
        assert rechazo.headers["www-authenticate"] == "Bearer"
        nueva = {"usuario": "cuenta-publica-prueba", "password": "clave-registro-prueba"}
        registro = cliente.post("/auth/registro", json=nueva)
        assert registro.status_code == 201
        assert set(registro.json()) == {"id", "usuario"}
        assert registro.json()["usuario"] == nueva["usuario"]
        assert cliente.post("/auth/registro", json=nueva).status_code == 409
        assert cliente.post("/auth/login", json=nueva).status_code == 200
        with sesiones() as sesion:
            cuentas = sesion.scalars(select(Cuenta)).all()
            assert len(cuentas) == 2
            assert all(password_prueba not in cuenta.password_hash for cuenta in cuentas)


def test_fallo_semilla_cancela_arranque_sin_exponer_datos_y_revierte(aplicacion, monkeypatch):
    app, sesiones = aplicacion
    cierres = []
    monkeypatch.setattr(sesiones.kw["bind"], "dispose", lambda: cierres.append(True))

    def rechazar_commit(sesion):
        raise ValueError("dato-sensible-exclusivo-prueba")

    event.listen(sesiones, "before_commit", rechazar_commit)
    with pytest.raises(RuntimeError) as error:
        with TestClient(app):
            pytest.fail("La aplicación no debe completar un arranque fallido")
    assert str(error.value) == "No se pudo inicializar la cuenta de RescueSync"
    assert error.value.__suppress_context__
    assert cierres == [True]
    with sesiones() as sesion:
        assert sesion.scalars(select(Cuenta)).all() == []


def test_configuracion_carga_semilla_desde_entorno(monkeypatch, cuenta_semilla):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    monkeypatch.setenv("USUARIO_RESCUESYNC", cuenta_semilla["usuario"])
    monkeypatch.setenv("PASSWORD_HASH_RESCUESYNC", cuenta_semilla["password_hash"])
    for variable in ("JWT_ISSUER", "JWT_AUDIENCE", "JWT_BACKEND_AUDIENCE"):
        monkeypatch.delenv(variable, raising=False)
    configuracion = cargar_configuracion()
    assert configuracion.usuario_rescuesync == cuenta_semilla["usuario"]
    assert configuracion.password_hash_rescuesync == cuenta_semilla["password_hash"]
    assert cuenta_semilla["password_hash"] not in repr(configuracion)
    assert configuracion.duracion_token == 3600
    assert configuracion.jwt_issuer == "rescuesync-cloud"
    assert configuracion.jwt_audience == "rescuesync-cloud"
    assert configuracion.jwt_backend_audience == "rescuesync-backend"


@pytest.mark.parametrize("variable", ["USUARIO_RESCUESYNC", "PASSWORD_HASH_RESCUESYNC"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_configuracion_incompleta_cancela_arranque_antes_de_base(
    aplicacion, monkeypatch, cuenta_semilla, variable, valor,
):
    import app.main as principal

    app, sesiones = aplicacion
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    monkeypatch.setenv("USUARIO_RESCUESYNC", cuenta_semilla["usuario"])
    monkeypatch.setenv("PASSWORD_HASH_RESCUESYNC", cuenta_semilla["password_hash"])
    if valor is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, valor)
    monkeypatch.setattr(principal, "cargar_configuracion", cargar_configuracion)
    inicios = []
    monkeypatch.setattr(principal, "iniciar_base_datos", lambda url: inicios.append(url))
    with pytest.raises(RuntimeError) as error:
        with TestClient(app):
            pytest.fail("La configuración incompleta debe cancelar el arranque")
    assert str(error.value) == "Definir USUARIO_RESCUESYNC y PASSWORD_HASH_RESCUESYNC"
    assert cuenta_semilla["password_hash"] not in str(error.value)
    assert inicios == []
    Base.metadata.create_all(sesiones.kw["bind"])
    with sesiones() as sesion:
        assert sesion.scalars(select(Cuenta)).all() == []


@pytest.mark.parametrize("variable", ["DATABASE_URL", "JWT_SECRET"])
def test_configuracion_base_ausente_conserva_modo_sin_base(monkeypatch, variable):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    for nombre in (variable, "USUARIO_RESCUESYNC", "PASSWORD_HASH_RESCUESYNC"):
        monkeypatch.delenv(nombre, raising=False)
    assert cargar_configuracion() is None
