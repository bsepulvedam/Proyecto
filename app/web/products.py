import os
from pathlib import Path
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.inventario_catalogo_service import (
    listar_empresas,
    listar_productos,
    listar_unidades,
    product_natural_key,
)
from app.services.product_import_service import (
    ProductImportError,
    ProductImportExecutionError,
    analyze_product_workbook,
    default_source_path,
    import_valid_products,
)
from app.services.product_import_correction_service import (
    analyze_product_corrections,
)


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def format_cl_number(value: object) -> str:
    if value is None:
        return "—"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    sign = "-" if number < 0 else ""
    integer, _, decimals = format(abs(number), "f").partition(".")
    grouped = ".".join(
        [integer[: len(integer) % 3]]
        + [integer[index:index + 3] for index in range(len(integer) % 3, len(integer), 3)]
    ).lstrip(".")
    decimals = decimals.rstrip("0")
    return f"{sign}{grouped}{',' + decimals if decimals else ''}"


templates.env.filters["cl_number"] = format_cl_number

router = APIRouter(tags=["web-productos"])


def _legacy_stock_states(db: Session, products: list) -> dict[str, str]:
    """Estado transitorio derivado del Excel; reemplazable por movimientos_stock."""
    try:
        report = analyze_product_corrections(
            source_path=_source_path(),
            products=products,
            units=listar_unidades(db),
        )
    except (ProductImportError, OSError):
        return {}
    states = {}
    for row in report.rows:
        if row.stock_minimo is None:
            continue
        if row.stock_actual <= 0:
            states[row.sku] = "SIN STOCK"
        elif row.stock_actual <= row.stock_minimo:
            states[row.sku] = "REPONER STOCK"
        else:
            states[row.sku] = "EN STOCK"
    return states


@router.get("/productos", response_class=HTMLResponse, name="products")
def products(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    all_products = listar_productos(db)
    stock_states = _legacy_stock_states(db, all_products)
    selected_company = request.query_params.get("empresa", "").strip().upper()
    selected_family = request.query_params.get("familia", "").strip().upper()
    selected_product_status = request.query_params.get("estado_producto", "TODOS").strip().upper()
    selected_stock_status = request.query_params.get("estado_stock", "TODOS").strip().upper()
    if selected_product_status not in {"TODOS", "ACTIVOS", "INACTIVOS"}:
        selected_product_status = "TODOS"
    if selected_stock_status not in {"TODOS", "EN STOCK", "REPONER STOCK", "SIN STOCK"}:
        selected_stock_status = "TODOS"
    search = request.query_params.get("q", "").strip()
    filtered_products = sorted([
        product
        for product in all_products
        if (not selected_company or product.empresa.codigo == selected_company)
        and (not selected_family or (product.familia or "").upper() == selected_family)
        and (
            selected_product_status == "TODOS"
            or (selected_product_status == "ACTIVOS" and product.activo)
            or (selected_product_status == "INACTIVOS" and not product.activo)
        )
        and (
            selected_stock_status == "TODOS"
            or stock_states.get(product.sku) == selected_stock_status
        )
        and (
            not search
            or search.casefold() in product.sku.casefold()
            or search.casefold() in product.nombre.casefold()
        )
    ], key=product_natural_key)
    family_source = [
        product for product in all_products
        if not selected_company or product.empresa.codigo == selected_company
    ]
    families = sorted({product.familia for product in family_source if product.familia})
    return templates.TemplateResponse(
        request=request,
        name="products/index.html",
        context={
            "products": filtered_products,
            "companies": sorted({product.empresa.codigo for product in all_products}),
            "families": families,
            "selected_company": selected_company,
            "selected_family": selected_family,
            "selected_product_status": selected_product_status,
            "selected_stock_status": selected_stock_status,
            "stock_states": stock_states,
            "search": search,
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


def _source_path() -> Path:
    configured_path = os.getenv("PRODUCT_IMPORT_FILE")
    return Path(configured_path) if configured_path else default_source_path()


def _analyze_source(db: Session, source_path: Path):
    return analyze_product_workbook(
        source_path=source_path,
        companies=listar_empresas(db),
        units=listar_unidades(db),
        existing_products=listar_productos(db),
    )


def _import_page_context(**values: object) -> dict[str, object]:
    context: dict[str, object] = {
        "demo": {
            "usuario": {
                "nombre": "Camila Soto",
                "rol": "Encargada de bodega",
            }
        },
        "active_page": "products",
        "page_title": "Importar productos",
        "page_eyebrow": "Importación controlada",
    }
    context.update(values)
    return context


@router.get("/productos/importar", response_class=HTMLResponse, name="product_import")
def product_import(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    source_path = _source_path()
    selected_filter = request.query_params.get("estado", "todos")
    if selected_filter not in {"todos", "validos", "advertencias", "errores"}:
        selected_filter = "todos"

    report = None
    error = None
    visible_rows = []
    try:
        report = _analyze_source(db, source_path)
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
        context=_import_page_context(
            report=report,
            visible_rows=visible_rows,
            selected_filter=selected_filter,
            source_filename=source_path.name,
            error=error,
            page_eyebrow="Vista previa controlada",
        ),
    )


@router.get(
    "/productos/importar/confirmar",
    response_class=HTMLResponse,
    name="confirm_product_import",
)
def confirm_product_import(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    source_path = _source_path()
    try:
        report = _analyze_source(db, source_path)
    except ProductImportError as exc:
        return templates.TemplateResponse(
            request=request,
            name="products/import_confirm.html",
            context=_import_page_context(report=None, error=str(exc)),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return templates.TemplateResponse(
        request=request,
        name="products/import_confirm.html",
        context=_import_page_context(report=report, error=None),
    )


@router.post(
    "/productos/importar",
    response_class=HTMLResponse,
    name="execute_product_import",
)
def execute_product_import(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    source_path = _source_path()
    try:
        report = _analyze_source(db, source_path)
        result = import_valid_products(db, report)
    except ProductImportError as exc:
        return templates.TemplateResponse(
            request=request,
            name="products/import_confirm.html",
            context=_import_page_context(report=None, error=str(exc)),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    except ProductImportExecutionError as exc:
        return templates.TemplateResponse(
            request=request,
            name="products/import_confirm.html",
            context=_import_page_context(report=report, error=str(exc)),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return templates.TemplateResponse(
        request=request,
        name="products/import_result.html",
        context=_import_page_context(result=result),
    )


@router.get(
    "/productos/corregir-importacion",
    response_class=HTMLResponse,
    name="product_import_correction",
)
def product_import_correction(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    source_path = _source_path()
    report = None
    error = None
    products = []
    try:
        products = listar_productos(db)
        report = analyze_product_corrections(
            source_path=source_path,
            products=products,
            units=listar_unidades(db),
        )
    except (ProductImportError, OSError) as exc:
        error = str(exc)
    return templates.TemplateResponse(
        request=request,
        name="products/import_correction.html",
        context=_import_page_context(
            report=report,
            error=error,
            source_filename=source_path.name,
            families=sorted({product.familia for product in products if product.familia}),
            page_title="Corregir importación",
            page_eyebrow="Vista previa sin escritura",
        ),
    )
