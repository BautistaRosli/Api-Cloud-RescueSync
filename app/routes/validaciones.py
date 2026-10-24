from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.validaciones import RespuestaEvaluacion
from app.schemas.validaciones import SolicitudEvaluacion
from app.services.validaciones_service import evaluar_ofertas
from app.openapi_examples import ERROR_401, ERROR_422, ERROR_503


router = APIRouter(dependencies=[Depends(obtener_cuenta)], responses={503: {"description": "Configuración o base no disponible", "content": {"application/json": {"example": ERROR_503}}}})

EJEMPLOS_SOLICITUD = {
    "consorcio": {
        "summary": "Consorcio (datos del seed)",
        "description": "Cruz Roja (1) es responsable y Médicos Sin Fronteras (3) apoya con Paramédicos (101).",
        "value": {
            "emergencia_id": 12,
            "lotes": [{"lote_id": 3, "tipo_recurso_id": 101, "cantidad_requerida": 40}],
            "ofertas": [{
                "oferta_id": 7, "lote_id": 3, "ong_responsable_id": 1,
                "aportes": [
                    {"ong_id": 1, "items": [{"tipo_recurso_id": 101, "cantidad": 20}]},
                    {"ong_id": 3, "items": [{"tipo_recurso_id": 101, "cantidad": 30}]},
                ],
            }],
        },
    },
    "con_problemas": {
        "summary": "ONG inexistente, inactiva y tipo equivocado",
        "description": "Nada de esto rompe la respuesta: aporta 0 y se explica en observaciones.",
        "value": {
            "emergencia_id": 12,
            "lotes": [{"lote_id": 4, "tipo_recurso_id": 105, "cantidad_requerida": 10}],
            "ofertas": [{
                "oferta_id": 8, "lote_id": 4, "ong_responsable_id": 4,
                "aportes": [
                    {"ong_id": 4, "items": [{"tipo_recurso_id": 105, "cantidad": 6},
                                            {"tipo_recurso_id": 103, "cantidad": 100}]},
                    {"ong_id": 6, "items": [{"tipo_recurso_id": 105, "cantidad": 3}]},
                    {"ong_id": 999, "items": [{"tipo_recurso_id": 105, "cantidad": 2}]},
                ],
            }],
        },
    },
}


@router.post(
    "/evaluar-ofertas",
    response_model=RespuestaEvaluacion,
    summary="Evaluar ofertas consolidadas de ONGs",
    description=(
        "Lo invoca Bonita al vencer el timer con el listado consolidado de ofertas. **No guarda las ofertas "
        "ni bloquea recursos** (eso es `POST /recursos/bloquear`): solo lee el inventario y responde.\n\n"
        "Por cada oferta y cada ONG verifica que la ONG exista y esté activa, que el tipo ofrecido coincida "
        "con el del lote y cuánto stock sin comprometer tiene realmente. No hay rechazo binario: devuelve un "
        "perfil con lo verificado por ONG, el `nivel_habilitacion` (COMPLETA / PARCIAL / SIN_DISPONIBILIDAD), "
        "la cobertura del lote y observaciones. En un consorcio la ONG responsable es PRINCIPAL y el resto "
        "APOYO_SECUNDARIO."
    ),
    responses={
        200: {"description": "Ofertas evaluadas", "content": {"application/json": {"example": {"emergencia_id": 12, "resultados": [{"oferta_id": 7, "lote_id": 3, "es_consorcio": True, "nivel_habilitacion": "COMPLETA", "cantidad_ofrecida": 50, "cantidad_verificada": 50, "cobertura_lote_pct": 100.0, "participantes": [{"ong_id": 1, "rol": "PRINCIPAL", "habilitada": True, "capacidades_habilitadas": [{"tipo_recurso_id": 101, "cantidad_ofrecida": 20, "cantidad_verificada": 20}]}], "observaciones": []}]}}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        422: {"description": "Solicitud inválida", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def evaluar(
    solicitud: SolicitudEvaluacion = Body(openapi_examples=EJEMPLOS_SOLICITUD),
    db: Session = Depends(obtener_sesion),
):
    return evaluar_ofertas(db, solicitud)
