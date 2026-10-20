from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dto.ong import OngCreada
from app.models import Ong
from app.schemas.ong import RegistroOng


def registrar_ong(db: Session, datos: RegistroOng) -> OngCreada:
    ong = Ong(**datos.model_dump())
    db.add(ong)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El CUIT ya está registrado") from None
    return OngCreada.model_validate(ong)
