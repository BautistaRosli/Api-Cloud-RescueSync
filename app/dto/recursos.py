from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class BloqueoRealizado(BaseModel):
    ong_id: int
    item_id: int
    cantidad: int
    estado: Literal["BLOQUEADO"] = "BLOQUEADO"


class RespuestaBloqueo(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "emergencia_id": 12,
                "lote_id": 3,
                "total_bloqueado": 15,
                "bloqueados": [
                    {"ong_id": 1, "item_id": 101, "cantidad": 2, "estado": "BLOQUEADO"},
                    {"ong_id": 3, "item_id": 101, "cantidad": 3, "estado": "BLOQUEADO"},
                    {"ong_id": 3, "item_id": 104, "cantidad": 10, "estado": "BLOQUEADO"},
                ],
            }
        }
    )

    emergencia_id: int
    lote_id: int | None = None
    total_bloqueado: int
    bloqueados: list[BloqueoRealizado]


class DisponibilidadTipo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "tipo_recurso_id": 1, "nombre": "Paramédicos", "unidad": "personas",
                "total": 120, "comprometido": 40, "disponible": 80,
            }
        },
    )

    tipo_recurso_id: int
    nombre: str
    unidad: str
    total: int
    comprometido: int
    disponible: int


class DisponibilidadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    disponibles: list[DisponibilidadTipo]
    mensaje: Optional[str] = None
