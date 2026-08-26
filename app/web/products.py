import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.inventario_catalogo_service import (
    listar_empresas,
    listar_productos,
    listar_unidades,
)
from app.services.product_import_service import (
    ProductImportError,
    analyze_product_workbook,
    default_source_path,
)


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(tags=["web-productos"])


@router.get("/productos", response_class=HTMLResponse, name="products")
def products(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="products/index.html",
        context={
            "products": listar_productos(db),
            "demo": {
                "usuario": {
                    "nombre": "Camila Soto",
                    "rol": "Encargada de bodega",
                }
            },
            "active_page": "products",
            "page_title": "Productos",
            "page_eyebrow": "Inventario",
        },
    )


@router.get("/productos/importar", response_class=HTMLResponse, name="product_import")
def product_import(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    configured_path = os.getenv("PRODUCT_IMPORT_FILE")
    source_path = Path(configured_path) if configured_path else default_source_path()
    selected_filter = request.query_params.get("estado", "todos")
    if selected_filter not in {"todos", "validos", "advertencias", "errores"}:
        selected_filter = "todos"

    report = None
    error = None
    visible_rows = []
    try:
        report = analyze_product_workbook(
            source_path=source_path,
            companies=listar_empresas(db),
            units=listar_unidades(db),
            existing_products=listar_productos(db),
        )
        status_by_filter = {
            "validos": "VALIDO",
            "advertencias": "ADVERTENCIA",
            "errores": "ERROR",
        }
        expected_status = status_by_filter.get(selected_filter)
        visible_rows = [
            row
            for row in report.rows
            if expected_status is None or row.validation_status == expected_status
        ]
    except ProductImportError as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request=request,
        name="products/import.html",
        context={
            "report": report,
            "visible_rows": visible_rows,
            "selected_filter": selected_filter,
            "source_filename": source_path.name,
            "error": error,
            "demo": {
                "usuario": {
                    "nombre": "Camila Soto",
                    "rol": "Encargada de bodega",
                }
            },
            "active_page": "products",
            "page_title": "Importar productos",
            "page_eyebrow": "Vista previa controlada",
        },
    )
