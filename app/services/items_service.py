from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.dto.items import ItemCreado, OngItemCreado
from app.models import Item, Ong, ong_items
from app.schemas.items import ItemCrear, ItemActualizar, OngItemCrear, OngItemActualizar


def crear_item(db: Session, datos: ItemCrear) -> ItemCreado:
    item = Item(**datos.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Error al crear el item") from None
    return ItemCreado.model_validate(item)


def listar_items(db: Session) -> list[ItemCreado]:
    items = db.execute(select(Item)).scalars().all()
    return [ItemCreado.model_validate(item) for item in items]


def obtener_item(db: Session, item_id: int) -> ItemCreado:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return ItemCreado.model_validate(item)


def actualizar_item(db: Session, item_id: int, datos: ItemActualizar) -> ItemCreado:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    update_data = datos.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Error al actualizar el item") from None
    return ItemCreado.model_validate(item)


def eliminar_item(db: Session, item_id: int) -> None:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()


def agregar_item_a_ong(db: Session, ong_id: int, datos: OngItemCrear) -> OngItemCreado:
    ong = db.get(Ong, ong_id)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG no encontrada")

    item = db.get(Item, datos.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    # Verificar si ya existe la relación
    existente = db.execute(
        select(ong_items).where(
            ong_items.c.ong_id == ong_id,
            ong_items.c.item_id == datos.item_id
        )
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="El item ya está en el inventario de esta ONG")

    # Insertar en tabla de asociación
    db.execute(
        ong_items.insert().values(
            ong_id=ong_id,
            item_id=datos.item_id,
            cantidad=datos.cantidad
        )
    )
    db.commit()

    return OngItemCreado(ong_id=ong_id, item_id=datos.item_id, cantidad=datos.cantidad, item=ItemCreado.model_validate(item))


def actualizar_cantidad_item_ong(db: Session, ong_id: int, item_id: int, datos: OngItemActualizar) -> OngItemCreado:
    ong = db.get(Ong, ong_id)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG no encontrada")

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    # Verificar que existe la relación
    existente = db.execute(
        select(ong_items).where(
            ong_items.c.ong_id == ong_id,
            ong_items.c.item_id == item_id
        )
    ).first()

    if not existente:
        raise HTTPException(status_code=404, detail="El item no está en el inventario de esta ONG")

    if datos.cantidad is not None:
        db.execute(
            ong_items.update()
            .where(
                ong_items.c.ong_id == ong_id,
                ong_items.c.item_id == item_id
            )
            .values(cantidad=datos.cantidad)
        )
        db.commit()

    return OngItemCreado(ong_id=ong_id, item_id=item_id, cantidad=datos.cantidad or existente.cantidad, item=ItemCreado.model_validate(item))


def eliminar_item_de_ong(db: Session, ong_id: int, item_id: int) -> None:
    ong = db.get(Ong, ong_id)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG no encontrada")

    existente = db.execute(
        select(ong_items).where(
            ong_items.c.ong_id == ong_id,
            ong_items.c.item_id == item_id
        )
    ).first()

    if not existente:
        raise HTTPException(status_code=404, detail="El item no está en el inventario de esta ONG")

    db.execute(
        ong_items.delete().where(
            ong_items.c.ong_id == ong_id,
            ong_items.c.item_id == item_id
        )
    )
    db.commit()


def obtener_ong_con_items(db: Session, ong_id: int) -> Ong:
    ong = db.execute(
        select(Ong)
        .options(selectinload(Ong.items))
        .where(Ong.id == ong_id)
    ).scalar_one_or_none()

    if not ong:
        raise HTTPException(status_code=404, detail="ONG no encontrada")

    return ong