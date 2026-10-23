from app.models import CompromisoRecurso, Item, Ong, ong_items


CREDENCIALES = {"usuario": "integracion", "password": "clave-de-prueba"}


def autorizar(cliente):
    respuesta = cliente.post("/auth/login", json=CREDENCIALES)
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def cargar_inventario(cliente):
    """Crea datos propios (independientes del seed aleatorio) y devuelve sus ids."""
    with cliente.app.state.sesiones.begin() as sesion:
        ongs = {
            "norte": Ong(cuit="prueba-1", razon_social="ONG Norte", email="norte@example.org"),
            "sur": Ong(cuit="prueba-2", razon_social="ONG Sur", email="sur@example.org"),
            "baja": Ong(cuit="prueba-3", razon_social="ONG de baja", email="baja@example.org", activa=False),
        }
        tipos = {
            "paramedicos": Item(nombre="Paramédicos prueba", unidad="personas"),
            "camiones": Item(nombre="Camiones prueba", unidad="unidades"),
        }
        sesion.add_all([*ongs.values(), *tipos.values()])
        sesion.flush()
        inventario = [
            ("norte", "paramedicos", 10), ("sur", "paramedicos", 5),
            ("baja", "paramedicos", 100), ("norte", "camiones", 4),
        ]
        for ong, tipo, cantidad in inventario:
            sesion.execute(ong_items.insert().values(ong_id=ongs[ong].id, item_id=tipos[tipo].id, cantidad=cantidad))
        compromisos = [
            ("norte", "paramedicos", 3, "COMPROMETIDO"),
            ("sur", "paramedicos", 4, "BLOQUEADO"),
            ("norte", "paramedicos", 7, "LIBERADO"),
            ("baja", "paramedicos", 50, "COMPROMETIDO"),
        ]
        for ong, tipo, cantidad, estado in compromisos:
            sesion.add(CompromisoRecurso(
                ong_id=ongs[ong].id, item_id=tipos[tipo].id, emergencia_id=1, cantidad=cantidad, estado=estado,
            ))
        return {nombre: ong.id for nombre, ong in ongs.items()} | {nombre: tipo.id for nombre, tipo in tipos.items()}
