from typing import Literal

from pydantic import BaseModel, ConfigDict


NivelHabilitacion = Literal["COMPLETA", "PARCIAL", "SIN_DISPONIBILIDAD"]
RolParticipante = Literal["PRINCIPAL", "APOYO_SECUNDARIO"]


class CapacidadHabilitada(BaseModel):
    tipo_recurso_id: int
    cantidad_ofrecida: int
    cantidad_verificada: int


class Participante(BaseModel):
    ong_id: int
    rol: RolParticipante
    habilitada: bool
    capacidades_habilitadas: list[CapacidadHabilitada]


class ResultadoOferta(BaseModel):
    oferta_id: int
    lote_id: int
    es_consorcio: bool
    nivel_habilitacion: NivelHabilitacion
    cantidad_ofrecida: int
    cantidad_verificada: int
    cobertura_lote_pct: float
    participantes: list[Participante]
    observaciones: list[str]


class RespuestaEvaluacion(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "emergencia_id": 12,
            "resultados": [{
                "oferta_id": 7, "lote_id": 3, "es_consorcio": True, "nivel_habilitacion": "PARCIAL",
                "cantidad_ofrecida": 5, "cantidad_verificada": 4, "cobertura_lote_pct": 80.0,
                "participantes": [
                    {"ong_id": 2, "rol": "PRINCIPAL", "habilitada": True, "capacidades_habilitadas": [
                        {"tipo_recurso_id": 1, "cantidad_ofrecida": 3, "cantidad_verificada": 3}]},
                    {"ong_id": 5, "rol": "APOYO_SECUNDARIO", "habilitada": True, "capacidades_habilitadas": [
                        {"tipo_recurso_id": 1, "cantidad_ofrecida": 2, "cantidad_verificada": 1}]},
                ],
                "observaciones": ["La ONG 5 ofreció 2 Paramédicos pero tiene 1 disponible"],
            }],
        }
    })

    emergencia_id: int
    resultados: list[ResultadoOferta]
