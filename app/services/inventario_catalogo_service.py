import re

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.inventario import ProductoCreate
from sqlalchemy.exc import IntegrityError


class CatalogError(ValueError):
    pass


def listar_empresas(db: Session) -> list[Empresa]:
    consulta = select(Empresa).order_by(Empresa.nombre.asc(), Empresa.id.asc())
    return list(db.scalars(consulta).all())


def listar_unidades(db: Session) -> list[UnidadMedida]:
    consulta = select(UnidadMedida).order_by(
        UnidadMedida.codigo.asc(), UnidadMedida.id.asc()
    )
    return list(db.scalars(consulta).all())


def listar_productos(db: Session) -> list[Producto]:
    consulta = (
        select(Producto)
        .options(
            joinedload(Producto.empresa),
            joinedload(Producto.unidad_stock),
            joinedload(Producto.unidad_contenido),
            joinedload(Producto.unidad_costo),
        )
        .order_by(Producto.empresa_id.asc(), Producto.sku.asc(), Producto.id.asc())
    )
    products = list(db.scalars(consulta).all())
    return sorted(products, key=product_natural_key)


def natural_sku_key(sku: str) -> tuple:
    """Convierte BOL-10 en una clave posterior a BOL-9, no a BOL-1."""
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", sku)
        if part
    )


def product_natural_key(product: Producto) -> tuple:
    company = product.empresa.codigo.upper()
    company_order = {"BOLIKLOR": 0, "ALM": 1}.get(company, 2)
    return company_order, natural_sku_key(product.sku), getattr(product, "id", 0)


def crear_producto(db: Session, data: ProductoCreate) -> Producto:
    if db.get(Empresa, data.empresa_id) is None:
        raise CatalogError("Empresa no válida.")
    unit_ids = {data.unidad_stock_id, data.unidad_costo_id}
    if data.unidad_contenido_id:
        unit_ids.add(data.unidad_contenido_id)
    if len(list(db.scalars(select(UnidadMedida).where(UnidadMedida.id.in_(unit_ids))).all())) != len(unit_ids):
        raise CatalogError("Una o más unidades no son válidas.")
    values = data.model_dump()
    values["sku"] = data.sku.strip().upper()
    values["nombre"] = data.nombre.strip().upper()
    values["tipo"] = data.tipo.strip().upper() if data.tipo else None
    values["familia"] = data.familia.strip().upper() if data.familia else None
    product = Producto(**values)
    try:
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    except IntegrityError as exc:
        db.rollback()
        raise CatalogError("El SKU ya existe en el catálogo.") from exc
