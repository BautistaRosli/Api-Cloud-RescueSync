from fastapi import HTTPException
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.dto.recursos import BloqueoRealizado, DisponibilidadResponse, DisponibilidadTipo, RespuestaBloqueo
from app.models import ESTADOS_COMPROMETIDOS, CompromisoRecurso, Item, Ong, ong_items
from app.schemas.recursos import SolicitudBloqueo


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
) -> DisponibilidadResponse:
    totales = _totales(db, tipo_recurso_id, ong_id)
    if not totales:
        return DisponibilidadResponse(
            disponibles=[],
            mensaje="No hay disponibilidad para los filtros aplicados"
        )
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
    return DisponibilidadResponse(disponibles=resultado)


def _comprometidos_por_par(
    db: Session, ong_ids: list[int], item_ids: list[int]
) -> dict[tuple[int, int], int]:
    consulta = (
        select(CompromisoRecurso.ong_id, CompromisoRecurso.item_id, func.sum(CompromisoRecurso.cantidad))
        .where(
            CompromisoRecurso.ong_id.in_(ong_ids),
            CompromisoRecurso.item_id.in_(item_ids),
            CompromisoRecurso.estado.in_(ESTADOS_COMPROMETIDOS),
        )
        .group_by(CompromisoRecurso.ong_id, CompromisoRecurso.item_id)
    )
    return {(ong, item): int(cantidad or 0) for ong, item, cantidad in db.execute(consulta)}


def disponible_por_ong_y_tipo(db: Session, ong_ids: set[int], item_ids: set[int]) -> dict[tuple[int, int], int]:
    """Stock sin comprometer de cada (ong_id, item_id) pedido. No filtra por ONG activa: eso lo decide quien llama."""
    if not ong_ids or not item_ids:
        return {}
    inventario = db.execute(
        select(ong_items.c.ong_id, ong_items.c.item_id, ong_items.c.cantidad)
        .where(ong_items.c.ong_id.in_(ong_ids), ong_items.c.item_id.in_(item_ids))
    )
    disponible = {(ong, item): int(cantidad or 0) for ong, item, cantidad in inventario}
    for (ong, item), cantidad in _comprometidos_por_par(db, sorted(ong_ids), sorted(item_ids)).items():
        if (ong, item) in disponible:
            disponible[(ong, item)] = max(disponible[(ong, item)] - cantidad, 0)
    return disponible


def _consulta_lock_ongs(ong_ids: list[int]):
    return select(Ong).where(Ong.id.in_(ong_ids)).order_by(Ong.id).with_for_update()


def _consulta_lock_items(item_ids: list[int]):
    return select(Item).where(Item.id.in_(item_ids)).order_by(Item.id).with_for_update()


def _consulta_lock_asignaciones(pares: list[tuple[int, int]]):
    return (
        select(ong_items.c.ong_id, ong_items.c.item_id, ong_items.c.cantidad)
        .where(tuple_(ong_items.c.ong_id, ong_items.c.item_id).in_(pares))
        .order_by(ong_items.c.ong_id, ong_items.c.item_id)
        .with_for_update()
    )


def _agrupar_pedidos(solicitud: SolicitudBloqueo) -> dict[tuple[int, int], int]:
    """Une items repetidos de una misma ONG para validar y bloquear el total una sola vez."""
    pedidos: dict[tuple[int, int], int] = {}
    for ong in solicitud.ongs:
        for item in ong.items:
            clave = (ong.ong_id, item.item_id)
            pedidos[clave] = pedidos.get(clave, 0) + item.cantidad
    return dict(sorted(pedidos.items()))


def bloquear_recursos(db: Session, solicitud: SolicitudBloqueo) -> RespuestaBloqueo:
    """Bloquea stock de una o varias ONGs escribiendo en `compromisos_recurso`.

    El stock vive en `ong_items`. Para que dos requests concurrentes no lean el
    mismo disponible y bloqueen de más, se toman locks de fila en PostgreSQL
    (`SELECT ... FOR UPDATE`) sobre las ONGs, el catálogo (`items`) y el
    inventario (`ong_items`) antes de calcular lo comprometido. Los locks se
    piden en orden de id para que dos requests con ONGs/items cruzados no se
    bloqueen entre sí (deadlock). Todo el bloqueo es atómico: si un item no
    tiene stock suficiente no se escribe ningún compromiso.
    """
    pedidos = _agrupar_pedidos(solicitud)
    ong_ids = sorted({ong_id for ong_id, _ in pedidos})
    item_ids = sorted({item_id for _, item_id in pedidos})

    try:
        ongs = {ong.id: ong for ong in db.scalars(_consulta_lock_ongs(ong_ids)).all()}
        for ong_id in ong_ids:
            ong = ongs.get(ong_id)
            if ong is None:
                raise HTTPException(status_code=404, detail=f"La ONG {ong_id} no existe")
            if not ong.activa:
                raise HTTPException(status_code=409, detail=f"La ONG {ong_id} no está activa")

        # 1) Lock del catálogo de recursos.
        items = db.scalars(_consulta_lock_items(item_ids)).all()
        existentes = {item.id for item in items}
        for item_id in item_ids:
            if item_id not in existentes:
                raise HTTPException(status_code=404, detail=f"El item {item_id} no existe")

        # 2) Lock de las asignaciones (inventario) de cada ONG. El orden por
        #    (ong_id, item_id) es el mismo en todos los requests.
        filas = db.execute(_consulta_lock_asignaciones(list(pedidos))).all()
        asignaciones = {(ong_id, item_id): int(cantidad or 0) for ong_id, item_id, cantidad in filas}

        # Los locks ya están tomados: esta lectura no puede competir con otro
        # bloqueo concurrente de los mismos pares (ong_id, item_id).
        comprometidos = _comprometidos_por_par(db, ong_ids, item_ids)

        for clave, cantidad in pedidos.items():
            if clave not in asignaciones:
                raise HTTPException(
                    status_code=409,
                    detail=f"La ONG {clave[0]} no tiene asignado el item {clave[1]}",
                )
            disponible = max(asignaciones[clave] - comprometidos.get(clave, 0), 0)
            if cantidad > disponible:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"La ONG {clave[0]} no tiene stock suficiente del item {clave[1]}: "
                        f"solicitado {cantidad}, disponible {disponible}"
                    ),
                )

        registros = [
            CompromisoRecurso(
                ong_id=ong_id,
                item_id=item_id,
                emergencia_id=solicitud.emergencia_id,
                lote_id=solicitud.lote_id,
                cantidad=cantidad,
                estado="BLOQUEADO",
            )
            for (ong_id, item_id), cantidad in pedidos.items()
        ]
        db.add_all(registros)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return RespuestaBloqueo(
        emergencia_id=solicitud.emergencia_id,
        lote_id=solicitud.lote_id,
        total_bloqueado=sum(pedidos.values()),
        bloqueados=[
            BloqueoRealizado(ong_id=ong_id, item_id=item_id, cantidad=cantidad)
            for (ong_id, item_id), cantidad in pedidos.items()
        ],
    )
