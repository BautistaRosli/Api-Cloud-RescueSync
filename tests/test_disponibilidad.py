from tests.datos_recursos import autorizar, cargar_inventario


def test_disponibilidad_agrupa_por_tipo_solo_ongs_activas(cliente):
    ids = cargar_inventario(cliente)
    respuesta = cliente.get("/recursos/disponibilidad", headers=autorizar(cliente))
    assert respuesta.status_code == 200
    por_tipo = {fila["tipo_recurso_id"]: fila for fila in respuesta.json()}
    # Norte 10 + Sur 5 (la ONG de baja no cuenta); comprometido 3 + 4 (LIBERADO no cuenta)
    assert por_tipo[ids["paramedicos"]] == {
        "tipo_recurso_id": ids["paramedicos"], "nombre": "Paramédicos prueba", "unidad": "personas",
        "total": 15, "comprometido": 7, "disponible": 8,
    }
    assert por_tipo[ids["camiones"]] == {
        "tipo_recurso_id": ids["camiones"], "nombre": "Camiones prueba", "unidad": "unidades",
        "total": 4, "comprometido": 0, "disponible": 4,
    }


def test_disponibilidad_filtra_por_tipo_y_ong(cliente):
    ids = cargar_inventario(cliente)
    cabeceras = autorizar(cliente)
    por_tipo = cliente.get("/recursos/disponibilidad", params={"tipo_recurso_id": ids["paramedicos"]}, headers=cabeceras)
    assert [fila["tipo_recurso_id"] for fila in por_tipo.json()] == [ids["paramedicos"]]

    por_ong = cliente.get("/recursos/disponibilidad", params={"ong_id": ids["sur"]}, headers=cabeceras).json()
    assert por_ong == [{
        "tipo_recurso_id": ids["paramedicos"], "nombre": "Paramédicos prueba", "unidad": "personas",
        "total": 5, "comprometido": 4, "disponible": 1,
    }]

    ambos = {"tipo_recurso_id": ids["camiones"], "ong_id": ids["norte"]}
    assert cliente.get("/recursos/disponibilidad", params=ambos, headers=cabeceras).json()[0]["total"] == 4
    assert cliente.get("/recursos/disponibilidad", params={"ong_id": ids["baja"]}, headers=cabeceras).json() == []
    assert cliente.get("/recursos/disponibilidad", params={"ong_id": 0}, headers=cabeceras).status_code == 422


def test_disponibilidad_sin_token_devuelve_401(cliente):
    respuesta = cliente.get("/recursos/disponibilidad")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Credenciales inválidas"}
