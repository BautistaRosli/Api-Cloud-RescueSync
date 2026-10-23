from pydantic import BaseModel, ConfigDict


class CompromisoLiberadoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ong_id: int
    item_id: int
    cantidad: int
    estado_anterior: str
    lote_id: int | None = None


class LiberacionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    emergencia_id: int
    total_liberado: int
    compromisos_liberados: list[CompromisoLiberadoDTO]