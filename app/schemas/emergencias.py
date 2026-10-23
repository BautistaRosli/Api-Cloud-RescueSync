from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field


Identificador = Annotated[int, Field(ge=1)]
Cantidad = Annotated[int, Field(ge=1)]


class CompromisoLiberado(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ong_id: int
    item_id: int
    cantidad: int
    estado_anterior: str
    lote_id: int | None = None


class LiberacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emergencia_id: int
    total_liberado: int
    compromisos_liberados: list[CompromisoLiberado]