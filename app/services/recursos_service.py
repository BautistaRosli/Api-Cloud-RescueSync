from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dto.recursos import DisponibilidadTipo
from app.models import ESTADOS_COMPROMETIDOS, CompromisoRecurso, Item, Ong, ong_items


def _filtrar(consulta, columna_ong, columna_item, tipo_recurso_id: int | None, ong_id: int | None):
    consulta = consulta.join(Ong, Ong.id == columna_ong).where(Ong.activa.is_(True))
    if tipo_recurso_id is not None:
        consulta = consulta.where(columna_item == tipo_recurso_id)
    if ong_id is not None:
        consulta = consulta.where(columna_ong == ong_id)
    return consulta


def _totales(db: Session, tipo_recurso_id: int | None, ong_id: int | None) -> dict[int, int]:
    consulta = select(ong_items.c.item_id, func.sum(ong_items.c.cantidad)).group_by(ong_items.c.item_id)
    consulta = _filtrar(consulta, ong_items.c.ong_id, ong_items.c.item_id, tipo_recurso_id, ong_id)
    return {item_id: int(total or 0) for item_id, total in db.execute(consulta)}


def _comprometidos(db: Session, tipo_recurso_id: int | None, ong_id: int | None) -> dict[int, int]:
    consulta = (
        select(CompromisoRecurso.item_id, func.sum(CompromisoRecurso.cantidad))
        .where(CompromisoRecurso.estado.in_(ESTADOS_COMPROMETIDOS))
        .group_by(CompromisoRecurso.item_id)
    )
    consulta = _filtrar(consulta, CompromisoRecurso.ong_id, CompromisoRecurso.item_id, tipo_recurso_id, ong_id)
    return {item_id: int(total or 0) for item_id, total in db.execute(consulta)}


def calcular_disponibilidad(
    db: Session, tipo_recurso_id: int | None = None, ong_id: int | None = None
) -> list[DisponibilidadTipo]:
    totales = _totales(db, tipo_recurso_id, ong_id)
    if not totales:
        return []
    comprometidos = _comprometidos(db, tipo_recurso_id, ong_id)
    tipos = db.scalars(select(Item).where(Item.id.in_(totales)).order_by(Item.id)).all()
    resultado = []
    for tipo in tipos:
        total = totales[tipo.id]
        comprometido = comprometidos.get(tipo.id, 0)
        resultado.append(DisponibilidadTipo(
            tipo_recurso_id=tipo.id, nombre=tipo.nombre, unidad=tipo.unidad,
            total=total, comprometido=comprometido, disponible=max(total - comprometido, 0),
        ))
    return resultado


def disponible_por_ong_y_tipo(db: Session, ong_ids: set[int], item_ids: set[int]) -> dict[tuple[int, int], int]:
    """Stock sin comprometer de cada (ong_id, item_id) pedido. No filtra por ONG activa: eso lo decide quien llama."""
    if not ong_ids or not item_ids:
        return {}
    inventario = db.execute(
        select(ong_items.c.ong_id, ong_items.c.item_id, ong_items.c.cantidad)
        .where(ong_items.c.ong_id.in_(ong_ids), ong_items.c.item_id.in_(item_ids))
    )
    disponible = {(ong, item): int(cantidad or 0) for ong, item, cantidad in inventario}
    comprometido = db.execute(
        select(CompromisoRecurso.ong_id, CompromisoRecurso.item_id, func.sum(CompromisoRecurso.cantidad))
        .where(
            CompromisoRecurso.ong_id.in_(ong_ids),
            CompromisoRecurso.item_id.in_(item_ids),
            CompromisoRecurso.estado.in_(ESTADOS_COMPROMETIDOS),
        )
        .group_by(CompromisoRecurso.ong_id, CompromisoRecurso.item_id)
    )
    for ong, item, cantidad in comprometido:
        if (ong, item) in disponible:
            disponible[(ong, item)] = max(disponible[(ong, item)] - int(cantidad or 0), 0)
    return disponible
