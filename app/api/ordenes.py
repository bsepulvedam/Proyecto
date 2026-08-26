from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.orden_trabajo import (
    OrdenTrabajoCreate,
    OrdenTrabajoRead,
    OrdenTrabajoResponse,
)
from app.services.orden_trabajo_service import crear_orden, listar_ordenes, obtener_orden


router = APIRouter(prefix="/api/ordenes-trabajo", tags=["ordenes-trabajo"])


@router.post(
    "",
    response_model=OrdenTrabajoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_orden_trabajo(
    orden: OrdenTrabajoCreate, db: Session = Depends(get_db)
) -> OrdenTrabajoResponse:
    try:
        orden_creada = crear_orden(db, orden)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible crear la orden de trabajo",
        ) from exc

    return OrdenTrabajoResponse(
        ok=True,
        numero_ot=orden_creada.numero_ot,
        mensaje="Orden de trabajo creada correctamente",
    )


@router.get("", response_model=list[OrdenTrabajoRead])
def listar_ordenes_trabajo(db: Session = Depends(get_db)) -> list[OrdenTrabajoRead]:
    return listar_ordenes(db)


@router.get("/{orden_id}", response_model=OrdenTrabajoRead)
def obtener_orden_trabajo(
    orden_id: int, db: Session = Depends(get_db)
) -> OrdenTrabajoRead:
    orden = obtener_orden(db, orden_id)
    if orden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OT no encontrada")
    return orden
