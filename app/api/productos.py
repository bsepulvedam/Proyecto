from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.models.producto import Producto

router = APIRouter(prefix="/api/productos", tags=["productos"])


@router.get("/buscar")
def search_products(q: str = Query(min_length=1, max_length=100), empresa_id: int = Query(gt=0), db: Session = Depends(get_db)) -> list[dict]:
    term = f"%{q.strip()}%"
    query = select(Producto).options(
        joinedload(Producto.unidad_stock), joinedload(Producto.unidad_contenido), joinedload(Producto.unidad_costo)
    ).where(
        Producto.empresa_id == empresa_id, Producto.activo.is_(True),
        or_(Producto.sku.ilike(term), Producto.nombre.ilike(term)),
    ).order_by(Producto.sku.asc()).limit(12)
    return [{
        "id": p.id, "sku": p.sku, "nombre": p.nombre,
        "unidad_presentacion": p.unidad_stock.codigo,
        "permite_decimales": p.unidad_stock.permite_decimales,
        "factor_conversion": str(p.factor_conversion),
        "unidad_contenido": p.unidad_contenido.codigo if p.unidad_contenido else None,
        "unidad_costo": p.unidad_costo.codigo if p.unidad_costo else None,
    } for p in db.scalars(query).all()]
