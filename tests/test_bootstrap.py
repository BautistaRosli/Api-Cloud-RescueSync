import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Configuracion, cargar_configuracion
from dataclasses import replace
from app.models import Base, Cuenta, Ong
from app.services.auth_service import generar_hash, verificar_password


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
            password_rescuesync=cuenta_semilla["password"],
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
            assert cuentas[0].password_hash != cuenta_semilla["password"]
            assert verificar_password(cuenta_semilla["password"], cuentas[0].password_hash)
            assert cuentas[0].password_hash.startswith("pbkdf2_sha256$600000$")
            assert sesion.scalars(select(Ong)).all() == []


@pytest.mark.parametrize("usuarios", [
    ["integracion"],
    ["anterior"],
    ["extra-primera", "integracion", "extra-ultima"],
    ["anterior", "extra-segunda", "extra-tercera"],
], ids=["actualiza-hash", "renombra-unica", "prefiere-coincidente", "reutiliza-primera"])
def test_arranque_reconcilia_unica_cuenta_y_conserva_ong(aplicacion, cuenta_semilla, usuarios):
    app, sesiones = aplicacion
    Base.metadata.create_all(sesiones.kw["bind"])
    hash_anterior = generar_hash("clave-anterior-ficticia")
    with sesiones.begin() as sesion:
        cuentas = [Cuenta(usuario=usuario, password_hash=hash_anterior) for usuario in usuarios]
        sesion.add_all(cuentas)
        sesion.add(Ong(cuit="30712345678", razon_social="ONG existente", email="ong@example.org"))
    cuenta_esperada = next((c for c in cuentas if c.usuario == cuenta_semilla["usuario"]), cuentas[0])
    with sesiones() as sesion:
        ongs_antes = [(o.id, o.cuit, o.razon_social, o.email) for o in sesion.scalars(select(Ong))]
    with TestClient(app) as cliente:
        with sesiones() as sesion:
            actuales = sesion.scalars(select(Cuenta)).all()
            assert len(actuales) == 1
            assert actuales[0].id == cuenta_esperada.id
            assert actuales[0].usuario == cuenta_semilla["usuario"]
            assert actuales[0].password_hash != cuenta_semilla["password"]
            assert verificar_password(cuenta_semilla["password"], actuales[0].password_hash)
            assert [(o.id, o.cuit, o.razon_social, o.email) for o in sesion.scalars(select(Ong))] == ongs_antes
        credenciales = {"usuario": cuenta_semilla["usuario"], "password": cuenta_semilla["password"]}
        assert cliente.post("/auth/login", json=credenciales).status_code == 200
        assert cliente.post("/auth/login", json={**credenciales, "password": "clave-anterior-ficticia"}).status_code == 401
        for usuario in usuarios:
            if usuario != cuenta_semilla["usuario"]:
                assert cliente.post("/auth/login", json={"usuario": usuario, "password": "clave-anterior-ficticia"}).status_code == 401


@pytest.mark.parametrize("cambia_usuario", [False, True])
def test_cambio_configuracion_actualiza_misma_fila_y_nuevo_login(aplicacion, monkeypatch, cuenta_semilla, cambia_usuario):
    import app.main as principal

    app, sesiones = aplicacion
    credenciales_antes = {"usuario": cuenta_semilla["usuario"], "password": cuenta_semilla["password"]}
    with TestClient(app) as cliente:
        assert cliente.post("/auth/login", json=credenciales_antes).status_code == 200
        with sesiones() as sesion:
            identificador = sesion.scalar(select(Cuenta.id))
    password_nuevo = "nueva-clave-ficticia"
    configuracion = replace(
        app.state.configuracion,
        usuario_rescuesync="nuevo-usuario" if cambia_usuario else cuenta_semilla["usuario"],
        password_rescuesync=password_nuevo,
    )
    monkeypatch.setattr(principal, "cargar_configuracion", lambda: configuracion)
    with TestClient(app) as cliente:
        with sesiones() as sesion:
            cuentas = sesion.scalars(select(Cuenta)).all()
            assert len(cuentas) == 1
            assert cuentas[0].id == identificador
            assert cuentas[0].usuario == configuracion.usuario_rescuesync
            assert cuentas[0].password_hash != password_nuevo
            assert verificar_password(password_nuevo, cuentas[0].password_hash)
        assert cliente.post("/auth/login", json=credenciales_antes).status_code == 401
        assert cliente.post("/auth/login", json={"usuario": configuracion.usuario_rescuesync, "password": password_nuevo}).status_code == 200
        assert cliente.post("/auth/login", json={"usuario": configuracion.usuario_rescuesync, "password": cuenta_semilla["password"]}).status_code == 401

    escrituras = []
    def registrar_escritura(conexion, cursor, sentencia, parametros, contexto, varios):
        if sentencia.split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            escrituras.append(sentencia.split()[0].upper())
    event.listen(sesiones.kw["bind"], "before_cursor_execute", registrar_escritura)
    with TestClient(app):
        with sesiones() as sesion:
            cuentas = sesion.scalars(select(Cuenta)).all()
            assert len(cuentas) == 1
            assert cuentas[0].id == identificador
            assert cuentas[0].usuario == configuracion.usuario_rescuesync
            assert cuentas[0].password_hash != password_nuevo
            assert verificar_password(password_nuevo, cuentas[0].password_hash)
    assert escrituras == ["UPDATE"]


def test_login_semilla_conserva_contrato(aplicacion, cuenta_semilla):
    app, sesiones = aplicacion
    with TestClient(app) as cliente:
        credenciales = {"usuario": cuenta_semilla["usuario"], "password": cuenta_semilla["password"]}
        respuesta = cliente.post("/auth/login", json=credenciales)
        assert respuesta.status_code == 200
        assert set(respuesta.json()) == {"access_token", "token_type", "expires_in"}
        assert respuesta.json()["token_type"] == "bearer"
        assert cuenta_semilla["password"] not in respuesta.text
        rechazo = cliente.post("/auth/login", json={**credenciales, "password": "incorrecta"})
        assert rechazo.status_code == 401
        assert rechazo.headers["www-authenticate"] == "Bearer"
        with sesiones() as sesion:
            assert len(sesion.scalars(select(Cuenta)).all()) == 1


@pytest.mark.parametrize("usuarios", [[], ["anterior"], ["extra", "integracion", "otra"]],
                         ids=["creacion", "actualizacion", "eliminacion"])
def test_fallo_semilla_cancela_arranque_sin_exponer_datos_y_revierte(aplicacion, monkeypatch, usuarios):
    app, sesiones = aplicacion
    Base.metadata.create_all(sesiones.kw["bind"])
    with sesiones.begin() as sesion:
        sesion.add_all(Cuenta(usuario=usuario, password_hash="hash-anterior-ficticio") for usuario in usuarios)
        sesion.add(Ong(cuit="30712345678", razon_social="ONG existente", email="ong@example.org"))
    with sesiones() as sesion:
        estado_antes = tuple(sesion.connection().connection.driver_connection.iterdump())
    cierres = []
    monkeypatch.setattr(sesiones.kw["bind"], "dispose", lambda: cierres.append(True))

    def rechazar_flush(sesion, contexto):
        raise ValueError("dato-sensible-exclusivo-prueba")

    event.listen(sesiones, "after_flush_postexec", rechazar_flush)
    with pytest.raises(RuntimeError) as error:
        with TestClient(app):
            pytest.fail("La aplicación no debe completar un arranque fallido")
    assert str(error.value) == "No se pudo inicializar la cuenta de RescueSync"
    assert error.value.__suppress_context__
    assert cierres == [True]
    with sesiones() as sesion:
        assert tuple(sesion.connection().connection.driver_connection.iterdump()) == estado_antes


def test_configuracion_carga_semilla_desde_entorno(monkeypatch, cuenta_semilla):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    monkeypatch.setenv("USUARIO_RESCUESYNC", cuenta_semilla["usuario"])
    monkeypatch.setenv("PASSWORD_RESCUESYNC", cuenta_semilla["password"])
    for variable in ("JWT_ISSUER", "JWT_AUDIENCE", "JWT_BACKEND_AUDIENCE"):
        monkeypatch.delenv(variable, raising=False)
    configuracion = cargar_configuracion()
    assert configuracion.usuario_rescuesync == cuenta_semilla["usuario"]
    assert configuracion.password_rescuesync == cuenta_semilla["password"]
    assert cuenta_semilla["password"] not in repr(configuracion)
    assert configuracion.duracion_token == 3600
    assert configuracion.jwt_issuer == "rescuesync-cloud"
    assert configuracion.jwt_audience == "rescuesync-cloud"
    assert configuracion.jwt_backend_audience == "rescuesync-backend"


@pytest.mark.parametrize("variable", ["USUARIO_RESCUESYNC", "PASSWORD_RESCUESYNC"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_configuracion_incompleta_cancela_arranque_antes_de_base(
    aplicacion, monkeypatch, cuenta_semilla, variable, valor,
):
    import app.main as principal

    app, sesiones = aplicacion
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    monkeypatch.setenv("USUARIO_RESCUESYNC", cuenta_semilla["usuario"])
    monkeypatch.setenv("PASSWORD_RESCUESYNC", cuenta_semilla["password"])
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
    assert str(error.value) == "Definir USUARIO_RESCUESYNC y PASSWORD_RESCUESYNC"
    assert cuenta_semilla["password"] not in str(error.value)
    assert inicios == []
    Base.metadata.create_all(sesiones.kw["bind"])
    with sesiones() as sesion:
        assert sesion.scalars(select(Cuenta)).all() == []


@pytest.mark.parametrize("variable", ["DATABASE_URL", "JWT_SECRET"])
def test_configuracion_base_ausente_conserva_modo_sin_base(monkeypatch, variable):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "secreto-exclusivo-configuracion-prueba")
    for nombre in (variable, "USUARIO_RESCUESYNC", "PASSWORD_RESCUESYNC"):
        monkeypatch.delenv(nombre, raising=False)
    assert cargar_configuracion() is None
