from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dto.emergencias import CompromisoLiberadoDTO, LiberacionResponseDTO
from app.models import CompromisoRecurso, ESTADOS_COMPROMETIDOS


def liberar_emergencia(db: Session, emergencia_id: int) -> LiberacionResponseDTO:
    """
    Libera todos los compromisos de una emergencia (cambia estado a LIBERADO).
    Solo afecta compromisos en estados comprometidos (BLOQUEADO, COMPROMETIDO).
    """
    # Buscar todos los compromisos de la emergencia que estén en estados comprometidos
    compromisos = db.scalars(
        select(CompromisoRecurso).where(
            CompromisoRecurso.emergencia_id == emergencia_id,
            CompromisoRecurso.estado.in_(ESTADOS_COMPROMETIDOS),
        )
    ).all()

    if not compromisos:
        return LiberacionResponseDTO(
            emergencia_id=emergencia_id,
            total_liberado=0,
            compromisos_liberados=[],
        )

    total_liberado = 0
    compromisos_liberados = []

    for compromiso in compromisos:
        estado_anterior = compromiso.estado
        compromiso.estado = "LIBERADO"
        total_liberado += compromiso.cantidad
        compromisos_liberados.append(
            CompromisoLiberadoDTO(
                ong_id=compromiso.ong_id,
                item_id=compromiso.item_id,
                cantidad=compromiso.cantidad,
                estado_anterior=estado_anterior,
                lote_id=compromiso.lote_id,
            )
        )

    db.commit()

    return LiberacionResponseDTO(
        emergencia_id=emergencia_id,
        total_liberado=total_liberado,
        compromisos_liberados=compromisos_liberados,
    )