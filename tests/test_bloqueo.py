from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import CompromisoRecurso
from app.services.recursos_service import (
    _consulta_lock_asignaciones,
    _consulta_lock_items,
    _consulta_lock_ongs,
)
from tests.datos_recursos import autorizar, cargar_inventario


def bloqueo(ids, asignaciones, emergencia_id=99, lote_id=7):
    return {
        "emergencia_id": emergencia_id,
        "lote_id": lote_id,
        "ongs": [
            {
                "ong_id": ids[ong],
                "items": [{"item_id": ids[item], "cantidad": cantidad} for item, cantidad in items],
            }
            for ong, items in asignaciones
        ],
    }


def compromisos(cliente, emergencia_id=99):
    with cliente.app.state.sesiones() as sesion:
        return list(sesion.scalars(
            select(CompromisoRecurso)
            .where(CompromisoRecurso.emergencia_id == emergencia_id)
            .order_by(CompromisoRecurso.ong_id, CompromisoRecurso.item_id)
        ))


def test_bloquear_varias_ongs_marca_items_y_afecta_disponibilidad(cliente):
    ids = cargar_inventario(cliente)
    respuesta = cliente.post(
        "/recursos/bloquear",
        json=bloqueo(ids, [("norte", [("paramedicos", 5)]), ("sur", [("paramedicos", 1)])]),
        headers=autorizar(cliente),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "emergencia_id": 99,
        "lote_id": 7,
        "total_bloqueado": 6,
        "bloqueados": [
            {"ong_id": ids["norte"], "item_id": ids["paramedicos"], "cantidad": 5, "estado": "BLOQUEADO"},
            {"ong_id": ids["sur"], "item_id": ids["paramedicos"], "cantidad": 1, "estado": "BLOQUEADO"},
        ],
    }

    filas = compromisos(cliente)
    assert [(fila.ong_id, fila.item_id, fila.cantidad, fila.lote_id, fila.estado) for fila in filas] == [
        (ids["norte"], ids["paramedicos"], 5, 7, "BLOQUEADO"),
        (ids["sur"], ids["paramedicos"], 1, 7, "BLOQUEADO"),
    ]

    disponibilidad = cliente.get("/recursos/disponibilidad", headers=autorizar(cliente)).json()
    por_tipo = {fila["tipo_recurso_id"]: fila for fila in disponibilidad}
    assert por_tipo[ids["paramedicos"]]["total"] == 15
    assert por_tipo[ids["paramedicos"]]["comprometido"] == 13
    assert por_tipo[ids["paramedicos"]]["disponible"] == 2


def test_bloquear_una_ong_con_varios_items(cliente):
    ids = cargar_inventario(cliente)
    respuesta = cliente.post(
        "/recursos/bloquear",
        json=bloqueo(ids, [("norte", [("paramedicos", 2), ("camiones", 3)])]),
        headers=autorizar(cliente),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total_bloqueado"] == 5
    assert {(fila.item_id, fila.cantidad) for fila in compromisos(cliente)} == {
        (ids["paramedicos"], 2), (ids["camiones"], 3),
    }


def test_bloquear_sin_stock_rechaza_todo_sin_escribir(cliente):
    ids = cargar_inventario(cliente)
    # Sur solo tiene 1 paramédico disponible; el primer item alcanza pero el segundo no.
    respuesta = cliente.post(
        "/recursos/bloquear",
        json=bloqueo(ids, [("norte", [("paramedicos", 1)]), ("sur", [("paramedicos", 2)])]),
        headers=autorizar(cliente),
    )
    assert respuesta.status_code == 409
    assert f"La ONG {ids['sur']} no tiene stock suficiente" in respuesta.json()["detail"]
    assert "disponible 1" in respuesta.json()["detail"]
    assert compromisos(cliente) == []


def test_bloquear_agrupa_items_repetidos_de_la_misma_ong(cliente):
    ids = cargar_inventario(cliente)
    respuesta = cliente.post(
        "/recursos/bloquear",
        json=bloqueo(ids, [("norte", [("paramedicos", 3), ("paramedicos", 4)])]),
        headers=autorizar(cliente),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["bloqueados"] == [
        {"ong_id": ids["norte"], "item_id": ids["paramedicos"], "cantidad": 7, "estado": "BLOQUEADO"},
    ]
    filas = compromisos(cliente)
    assert len(filas) == 1
    assert filas[0].cantidad == 7


def test_bloquear_rechaza_ong_inexistente_inactiva_e_item_no_asignado(cliente):
    ids = cargar_inventario(cliente)
    cabeceras = autorizar(cliente)

    casos = [
        ({"emergencia_id": 77, "ongs": [{"ong_id": 999, "items": [{"item_id": ids["paramedicos"], "cantidad": 1}]}]},
         404, "La ONG 999 no existe"),
        (bloqueo(ids, [("baja", [("paramedicos", 1)])], emergencia_id=77),
         409, f"La ONG {ids['baja']} no está activa"),
        (bloqueo(ids, [("sur", [("camiones", 1)])], emergencia_id=77),
         409, f"La ONG {ids['sur']} no tiene asignado el item {ids['camiones']}"),
        ({"emergencia_id": 77, "ongs": [{"ong_id": ids["norte"], "items": [{"item_id": 999, "cantidad": 1}]}]},
         404, "El item 999 no existe"),
    ]
    for cuerpo, estado, detalle in casos:
        respuesta = cliente.post("/recursos/bloquear", json=cuerpo, headers=cabeceras)
        assert respuesta.status_code == estado
        assert detalle in respuesta.json()["detail"]
    assert compromisos(cliente, 77) == []


def test_bloquear_acepta_asignaciones_planas_y_tipo_recurso_id(cliente):
    ids = cargar_inventario(cliente)
    respuesta = cliente.post(
        "/recursos/bloquear",
        json={
            "emergencia_id": 55,
            "items": [
                {"ong_id": ids["norte"], "tipo_recurso_id": ids["paramedicos"], "cantidad": 2},
                {"ong_id": ids["sur"], "tipo_recurso_id": ids["paramedicos"], "cantidad": 1},
            ],
        },
        headers=autorizar(cliente),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["lote_id"] is None
    assert len(compromisos(cliente, 55)) == 2


def test_bloquear_exige_token_y_cuerpo_valido(cliente):
    ids = cargar_inventario(cliente)
    cuerpo = bloqueo(ids, [("norte", [("paramedicos", 1)])])

    sin_token = cliente.post("/recursos/bloquear", json=cuerpo)
    assert sin_token.status_code == 401

    cabeceras = autorizar(cliente)
    for invalido in [
        {},
        {"emergencia_id": 123, "ongs": []},
        {"emergencia_id": 123, "ongs": [{"ong_id": ids["norte"], "items": []}]},
        {
            "emergencia_id": 123,
            "ongs": [{"ong_id": ids["norte"], "items": [{"item_id": ids["paramedicos"], "cantidad": 0}]}],
        },
    ]:
        assert cliente.post("/recursos/bloquear", json=invalido, headers=cabeceras).status_code == 422
    assert compromisos(cliente, 123) == []


def test_el_bloqueo_pide_locks_de_fila_en_postgresql():
    consultas = [
        _consulta_lock_ongs([1, 2]),
        _consulta_lock_items([101, 105]),
        _consulta_lock_asignaciones([(1, 101), (2, 105)]),
    ]
    for consulta in consultas:
        sentencia = str(consulta.compile(dialect=postgresql.dialect()))
        assert sentencia.rstrip().endswith("FOR UPDATE")
