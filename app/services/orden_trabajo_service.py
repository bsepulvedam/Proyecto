import logging

from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session, selectinload

from app.models.orden_trabajo import OrdenTrabajo
from app.models.producto_ot import ProductoOT
from app.schemas.orden_trabajo import OrdenTrabajoCreate


logger = logging.getLogger(__name__)
numero_ot_sequence = Sequence("numero_ot_seq")


def crear_orden(db: Session, datos: OrdenTrabajoCreate) -> OrdenTrabajo:
    try:
        numero_ot = db.execute(select(numero_ot_sequence.next_value())).scalar_one()
        valores = datos.model_dump(exclude={"productos"})
        orden = OrdenTrabajo(numero_ot=numero_ot, **valores)
        orden.productos = [
            ProductoOT(**producto.model_dump()) for producto in datos.productos
        ]
        db.add(orden)
        db.commit()
        db.refresh(orden)
        return orden
    except Exception:
        db.rollback()
        logger.exception("Error al crear la orden de trabajo")
        raise


def listar_ordenes(db: Session) -> list[OrdenTrabajo]:
    consulta = (
        select(OrdenTrabajo)
        .options(selectinload(OrdenTrabajo.productos))
        .order_by(OrdenTrabajo.created_at.desc(), OrdenTrabajo.id.desc())
    )
    return list(db.scalars(consulta).all())


def obtener_orden(db: Session, orden_id: int) -> OrdenTrabajo | None:
    consulta = (
        select(OrdenTrabajo)
        .options(selectinload(OrdenTrabajo.productos))
        .where(OrdenTrabajo.id == orden_id)
    )
    return db.scalar(consulta)
