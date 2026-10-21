from tests.datos_recursos import autorizar, cargar_inventario


def solicitud(ids, aportes, responsable="norte", requerida=10, tipo="paramedicos", lote_id=3):
    return {
        "emergencia_id": 12,
        "lotes": [{"lote_id": 3, "tipo_recurso_id": ids[tipo], "cantidad_requerida": requerida}],
        "ofertas": [{
            "oferta_id": 7, "lote_id": lote_id,
            "ong_responsable_id": ids.get(responsable, responsable),
            "aportes": [
                {"ong_id": ids.get(ong, ong), "items": [{"tipo_recurso_id": ids[t], "cantidad": c} for t, c in items]}
                for ong, items in aportes
            ],
        }],
    }


def evaluar(cliente, cuerpo):
    respuesta = cliente.post("/validaciones/evaluar-ofertas", json=cuerpo, headers=autorizar(cliente))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["emergencia_id"] == 12
    return respuesta.json()["resultados"][0]


def test_oferta_individual_completa(cliente):
    ids = cargar_inventario(cliente)
    # Norte tiene 10 paramédicos, 3 comprometidos => 7 disponibles
    resultado = evaluar(cliente, solicitud(ids, [("norte", [("paramedicos", 7)])], requerida=7))
    assert resultado == {
        "oferta_id": 7, "lote_id": 3, "es_consorcio": False, "nivel_habilitacion": "COMPLETA",
        "cantidad_ofrecida": 7, "cantidad_verificada": 7, "cobertura_lote_pct": 100.0,
        "participantes": [{
            "ong_id": ids["norte"], "rol": "PRINCIPAL", "habilitada": True,
            "capacidades_habilitadas": [
                {"tipo_recurso_id": ids["paramedicos"], "cantidad_ofrecida": 7, "cantidad_verificada": 7}],
        }],
        "observaciones": [],
    }


def test_consorcio_asigna_roles_principal_y_apoyo(cliente):
    ids = cargar_inventario(cliente)
    cuerpo = solicitud(ids, [("norte", [("paramedicos", 5)]), ("sur", [("paramedicos", 1)])], responsable="sur")
    resultado = evaluar(cliente, cuerpo)
    assert resultado["es_consorcio"] is True
    assert resultado["nivel_habilitacion"] == "COMPLETA"
    roles = {p["ong_id"]: p["rol"] for p in resultado["participantes"]}
    assert roles == {ids["sur"]: "PRINCIPAL", ids["norte"]: "APOYO_SECUNDARIO"}
    assert all(p["habilitada"] for p in resultado["participantes"])
    assert resultado["cobertura_lote_pct"] == 60.0


def test_oferta_parcial_informa_cuanto_se_verifica(cliente):
    ids = cargar_inventario(cliente)
    # Sur tiene 5, 4 bloqueados => 1 disponible
    cuerpo = solicitud(ids, [("norte", [("paramedicos", 3)]), ("sur", [("paramedicos", 2)])], requerida=5)
    resultado = evaluar(cliente, cuerpo)
    assert resultado["nivel_habilitacion"] == "PARCIAL"
    assert (resultado["cantidad_ofrecida"], resultado["cantidad_verificada"]) == (5, 4)
    assert resultado["cobertura_lote_pct"] == 80.0
    sur = next(p for p in resultado["participantes"] if p["ong_id"] == ids["sur"])
    assert sur["capacidades_habilitadas"] == [
        {"tipo_recurso_id": ids["paramedicos"], "cantidad_ofrecida": 2, "cantidad_verificada": 1}]
    assert resultado["observaciones"] == [f"La ONG {ids['sur']} ofreció 2 Paramédicos prueba pero tiene 1 disponible"]


def test_ong_inexistente_o_inactiva_aporta_cero_y_se_explica(cliente):
    ids = cargar_inventario(cliente)
    cuerpo = solicitud(ids, [("norte", [("paramedicos", 2)]), (999, [("paramedicos", 4)]), ("baja", [("paramedicos", 1)])])
    resultado = evaluar(cliente, cuerpo)
    assert resultado["nivel_habilitacion"] == "PARCIAL"
    assert (resultado["cantidad_ofrecida"], resultado["cantidad_verificada"]) == (7, 2)
    inexistente = next(p for p in resultado["participantes"] if p["ong_id"] == 999)
    assert inexistente == {"ong_id": 999, "rol": "APOYO_SECUNDARIO", "habilitada": False, "capacidades_habilitadas": []}
    assert "La ONG 999 no existe: su aporte de 4 no se cuenta" in resultado["observaciones"]
    assert f"La ONG {ids['baja']} no está activa: su aporte de 1 no se cuenta" in resultado["observaciones"]


def test_tipo_distinto_al_lote_y_lote_desconocido_no_rompen(cliente):
    ids = cargar_inventario(cliente)
    resultado = evaluar(cliente, solicitud(ids, [("norte", [("camiones", 2)])]))
    assert resultado["nivel_habilitacion"] == "SIN_DISPONIBILIDAD"
    assert resultado["participantes"][0]["habilitada"] is False
    assert any("requiere Paramédicos prueba" in obs for obs in resultado["observaciones"])

    resultado = evaluar(cliente, solicitud(ids, [("norte", [("paramedicos", 2)])], lote_id=99))
    assert resultado["cantidad_verificada"] == 0
    assert resultado["cobertura_lote_pct"] == 0.0
    assert "El lote 99 no figura entre los lotes de la solicitud" in resultado["observaciones"]


def test_aportes_repetidos_de_una_ong_no_cuentan_stock_dos_veces(cliente):
    ids = cargar_inventario(cliente)
    cuerpo = solicitud(ids, [("norte", [("paramedicos", 5)]), ("norte", [("paramedicos", 5)])])
    resultado = evaluar(cliente, cuerpo)
    assert resultado["es_consorcio"] is False
    assert (resultado["cantidad_ofrecida"], resultado["cantidad_verificada"]) == (10, 7)


def test_evaluar_no_modifica_la_base_y_exige_token(cliente):
    ids = cargar_inventario(cliente)
    cuerpo = solicitud(ids, [("norte", [("paramedicos", 3)])])
    with cliente.app.state.sesiones() as sesion:
        antes = tuple(sesion.connection().connection.driver_connection.iterdump())
    evaluar(cliente, cuerpo)
    with cliente.app.state.sesiones() as sesion:
        assert tuple(sesion.connection().connection.driver_connection.iterdump()) == antes
    assert cliente.post("/validaciones/evaluar-ofertas", json=cuerpo).status_code == 401


def test_solicitud_mal_formada_devuelve_422(cliente):
    cabeceras = autorizar(cliente)
    respuesta = cliente.post("/validaciones/evaluar-ofertas", json={"emergencia_id": 1, "lotes": []}, headers=cabeceras)
    assert respuesta.status_code == 422
