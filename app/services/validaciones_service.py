from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dto.validaciones import (
    CapacidadHabilitada,
    NivelHabilitacion,
    Participante,
    ResultadoOferta,
    RespuestaEvaluacion,
    RolParticipante,
)
from app.models import Item, Ong
from app.schemas.validaciones import AporteOng, LoteSolicitado, OfertaConsolidada, SolicitudEvaluacion
from app.services.recursos_service import disponible_por_ong_y_tipo


# Reglas de negocio: funciones chicas para poder cambiarlas sin tocar el recorrido de las ofertas.

def determinar_rol(ong_id: int, ong_responsable_id: int) -> RolParticipante:
    return "PRINCIPAL" if ong_id == ong_responsable_id else "APOYO_SECUNDARIO"


def determinar_nivel(cantidad_ofrecida: int, cantidad_verificada: int) -> NivelHabilitacion:
    if cantidad_verificada <= 0:
        return "SIN_DISPONIBILIDAD"
    if cantidad_verificada >= cantidad_ofrecida:
        return "COMPLETA"
    return "PARCIAL"


def calcular_cobertura(cantidad_verificada: int, cantidad_requerida: int) -> float:
    if cantidad_requerida <= 0:
        return 0.0
    return round(min(cantidad_verificada / cantidad_requerida, 1) * 100, 1)


def participante_habilitado(ong: Ong | None, cantidad_verificada: int) -> bool:
    return ong is not None and ong.activa and cantidad_verificada > 0


class _Contexto:
    """Datos leídos una sola vez de la base para toda la solicitud."""

    def __init__(self, db: Session, solicitud: SolicitudEvaluacion):
        ong_ids = {aporte.ong_id for oferta in solicitud.ofertas for aporte in oferta.aportes}
        tipo_ids = {lote.tipo_recurso_id for lote in solicitud.lotes} | {
            item.tipo_recurso_id for oferta in solicitud.ofertas for aporte in oferta.aportes for item in aporte.items
        }
        self.lotes = {lote.lote_id: lote for lote in solicitud.lotes}
        self.ongs = {ong.id: ong for ong in db.scalars(select(Ong).where(Ong.id.in_(ong_ids)))} if ong_ids else {}
        self.tipos = {item.id: item for item in db.scalars(select(Item).where(Item.id.in_(tipo_ids)))} if tipo_ids else {}
        self.disponible = disponible_por_ong_y_tipo(db, set(self.ongs), tipo_ids)

    def nombre_tipo(self, tipo_recurso_id: int) -> str:
        tipo = self.tipos.get(tipo_recurso_id)
        return tipo.nombre if tipo else f"el tipo de recurso {tipo_recurso_id}"


def _agrupar_aportes(aportes: list[AporteOng]) -> dict[int, list]:
    """Une los aportes repetidos de una misma ONG, respetando el orden en que llegaron."""
    agrupados: dict[int, list] = {}
    for aporte in aportes:
        agrupados.setdefault(aporte.ong_id, []).extend(aporte.items)
    return agrupados


def _evaluar_participante(
    ctx: _Contexto, ong_id: int, items: list, oferta: OfertaConsolidada, lote: LoteSolicitado | None,
    observaciones: list[str],
) -> tuple[Participante, int, int]:
    ofrecida = sum(item.cantidad for item in items)
    ong = ctx.ongs.get(ong_id)
    capacidades: list[CapacidadHabilitada] = []
    verificada = 0

    if ong is None:
        observaciones.append(f"La ONG {ong_id} no existe: su aporte de {ofrecida} no se cuenta")
    elif not ong.activa:
        observaciones.append(f"La ONG {ong_id} no está activa: su aporte de {ofrecida} no se cuenta")
    elif lote is not None:
        restante: dict[int, int] = {}
        for item in items:
            nombre = ctx.nombre_tipo(item.tipo_recurso_id)
            if item.tipo_recurso_id != lote.tipo_recurso_id:
                observaciones.append(
                    f"La ONG {ong_id} ofreció {item.cantidad} de {nombre} pero el lote {lote.lote_id} "
                    f"requiere {ctx.nombre_tipo(lote.tipo_recurso_id)}"
                )
                continue
            clave = (ong_id, item.tipo_recurso_id)
            if clave not in ctx.disponible:
                observaciones.append(f"La ONG {ong_id} ofreció {item.cantidad} {nombre} pero no los tiene en su inventario")
                continue
            disponible = restante.setdefault(item.tipo_recurso_id, ctx.disponible[clave])
            item_verificado = min(item.cantidad, disponible)
            restante[item.tipo_recurso_id] = disponible - item_verificado
            if item_verificado < item.cantidad:
                observaciones.append(
                    f"La ONG {ong_id} ofreció {item.cantidad} {nombre} pero tiene {disponible} disponible"
                )
            if item_verificado > 0:
                capacidades.append(CapacidadHabilitada(
                    tipo_recurso_id=item.tipo_recurso_id, cantidad_ofrecida=item.cantidad,
                    cantidad_verificada=item_verificado,
                ))
            verificada += item_verificado

    participante = Participante(
        ong_id=ong_id,
        rol=determinar_rol(ong_id, oferta.ong_responsable_id),
        habilitada=participante_habilitado(ong, verificada),
        capacidades_habilitadas=capacidades,
    )
    return participante, ofrecida, verificada


def _evaluar_oferta(ctx: _Contexto, oferta: OfertaConsolidada) -> ResultadoOferta:
    observaciones: list[str] = []
    lote = ctx.lotes.get(oferta.lote_id)
    if lote is None:
        observaciones.append(f"El lote {oferta.lote_id} no figura entre los lotes de la solicitud")

    aportes = _agrupar_aportes(oferta.aportes)
    if oferta.ong_responsable_id not in aportes:
        observaciones.append(f"La ONG responsable {oferta.ong_responsable_id} no figura entre los aportes de la oferta")

    participantes = []
    total_ofrecido = total_verificado = 0
    for ong_id, items in aportes.items():
        participante, ofrecida, verificada = _evaluar_participante(ctx, ong_id, items, oferta, lote, observaciones)
        participantes.append(participante)
        total_ofrecido += ofrecida
        total_verificado += verificada

    if lote is not None and total_verificado > lote.cantidad_requerida:
        observaciones.append(
            f"Lo verificado ({total_verificado}) supera lo requerido por el lote ({lote.cantidad_requerida})"
        )

    return ResultadoOferta(
        oferta_id=oferta.oferta_id,
        lote_id=oferta.lote_id,
        es_consorcio=len(aportes) > 1,
        nivel_habilitacion=determinar_nivel(total_ofrecido, total_verificado),
        cantidad_ofrecida=total_ofrecido,
        cantidad_verificada=total_verificado,
        cobertura_lote_pct=calcular_cobertura(total_verificado, lote.cantidad_requerida if lote else 0),
        participantes=participantes,
        observaciones=observaciones,
    )


def evaluar_ofertas(db: Session, solicitud: SolicitudEvaluacion) -> RespuestaEvaluacion:
    """Solo lectura: no guarda las ofertas ni bloquea recursos. Cada oferta se evalúa contra el stock actual."""
    ctx = _Contexto(db, solicitud)
    return RespuestaEvaluacion(
        emergencia_id=solicitud.emergencia_id,
        resultados=[_evaluar_oferta(ctx, oferta) for oferta in solicitud.ofertas],
    )
