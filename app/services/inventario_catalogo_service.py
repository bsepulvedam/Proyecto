from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida


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
        .order_by(Producto.empresa_id.asc(), Producto.nombre.asc(), Producto.id.asc())
    )
    return list(db.scalars(consulta).all())
