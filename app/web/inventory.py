from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.movimiento_inventario import LineaRecepcionCreate, RecepcionCreate
from app.services.inventario_catalogo_service import listar_empresas, product_natural_key
from app.services.inventario_movimiento_service import InventoryMovementError, create_receipt, get_movement, list_movements
from app.services.inventory_stock_service import MODE_TRANSITION, inventory_stock_rows, transactional_inventory_values

router = APIRouter(prefix="/inventario", tags=["web-inventario"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
DEMO = {"usuario": {"nombre": "Camila Soto", "rol": "Encargada de bodega"}}


def money(value):
    number = Decimal(str(value or 0))
    rendered = f"{number:,.2f}"
    integer, decimals = rendered.split(".")
    integer = integer.replace(",", ".")
    return f"${integer}{',' + decimals if decimals != '00' else ''}"


templates.env.filters["money_cl"] = money


def context(**values):
    data = {"demo": DEMO, "active_page": "inventory", "page_title": "Inventario", "page_eyebrow": "Motor transaccional"}
    data.update(values)
    return data


async def _form(request: Request):
    return parse_qs((await request.body()).decode(), keep_blank_values=True, max_num_fields=500)


def _first(form, name):
    return form.get(name, [""])[0].strip()


def _receipt_from_form(form) -> RecepcionCreate:
    product_ids, quantities, costs = form.get("producto_id", []), form.get("cantidad", []), form.get("costo_unitario", [])
    if not product_ids:
        raise InventoryMovementError("Agrega al menos un producto al carrito.")
    lines = []
    for index, product_id in enumerate(product_ids):
        try:
            lines.append(LineaRecepcionCreate(
                producto_id=int(product_id), cantidad_presentaciones=Decimal(quantities[index].replace(",", ".")),
                costo_unitario=Decimal(costs[index].replace(",", ".")),
            ))
        except (ValueError, InvalidOperation, IndexError, ValidationError) as exc:
            raise InventoryMovementError(f"Revisa cantidad y costo de la línea {index + 1}.") from exc
    try:
        return RecepcionCreate(
            empresa_id=int(_first(form, "empresa_id")), fecha=date.today(),
            guia_despacho=_first(form, "guia_despacho") or None,
            referencia=_first(form, "referencia") or None,
            observaciones=_first(form, "observaciones") or None, lineas=lines,
        )
    except (ValueError, ValidationError) as exc:
        raise InventoryMovementError("Selecciona una empresa válida.") from exc


@router.get("/recepcion", response_class=HTMLResponse, name="inventory_receipt")
def receipt_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="inventory/receipt.html", context=context(
        empresas=listar_empresas(db), fecha=date.today(), error=None,
        active_page="inventory_receipt", page_title="Recepción de productos",
    ))


@router.post("/recepcion", response_class=HTMLResponse, name="create_inventory_receipt")
async def receipt_create(request: Request, db: Session = Depends(get_db)):
    try:
        movement = create_receipt(db, _receipt_from_form(await _form(request)))
    except (InventoryMovementError, ValidationError) as exc:
        return templates.TemplateResponse(request=request, name="inventory/receipt.html", context=context(
            empresas=listar_empresas(db), fecha=date.today(), error=str(exc),
            active_page="inventory_receipt", page_title="Recepción de productos",
        ), status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    except Exception:
        return templates.TemplateResponse(request=request, name="inventory/receipt.html", context=context(
            empresas=listar_empresas(db), fecha=date.today(),
            error="No fue posible registrar la recepción. No se guardó ninguna línea.",
            active_page="inventory_receipt", page_title="Recepción de productos",
        ), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return templates.TemplateResponse(request=request, name="inventory/receipt_success.html", context=context(
        movement=movement, active_page="inventory_receipt", page_title="Recepción confirmada",
    ), status_code=status.HTTP_201_CREATED)


@router.get("/movimientos", response_class=HTMLResponse, name="inventory_movements")
def movements(request: Request, db: Session = Depends(get_db)):
    company_text = request.query_params.get("empresa_id", "").strip()
    movement_type = request.query_params.get("tipo", "").strip().upper()
    from_text = request.query_params.get("fecha_desde", "").strip()
    to_text = request.query_params.get("fecha_hasta", "").strip()
    search = request.query_params.get("q", "").strip()
    try:
        company_id = int(company_text) if company_text else None
    except ValueError:
        company_id = None
    try:
        from_date = date.fromisoformat(from_text) if from_text else None
        to_date = date.fromisoformat(to_text) if to_text else None
    except ValueError:
        from_date = to_date = None
    return templates.TemplateResponse(request=request, name="inventory/movements.html", context=context(
        movements=list_movements(db, company_id, movement_type, from_date, to_date, search),
        empresas=listar_empresas(db), selected_company=company_text, selected_type=movement_type,
        date_from=from_text, date_to=to_text, search=search,
        movement_types=["RECEPCION", "AJUSTE_INICIAL", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"],
        active_page="inventory_movements", page_title="Movimientos de inventario",
    ))


@router.get("/movimientos/{movement_id}", response_class=HTMLResponse, name="inventory_movement_detail")
def movement_detail(request: Request, movement_id: int, db: Session = Depends(get_db)):
    movement = get_movement(db, movement_id)
    if movement is None:
        return HTMLResponse("Movimiento no encontrado", status_code=404)
    return templates.TemplateResponse(request=request, name="inventory/movement_detail.html", context=context(
        movement=movement, active_page="inventory_movements", page_title=movement.numero_documento,
    ))


def _decimal_filter(value: str) -> Decimal | None:
    if not value.strip():
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _stock_page(request: Request, db: Session, company_code: str):
    mode, all_rows = inventory_stock_rows(db)
    search = request.query_params.get("q", "").strip()
    family = request.query_params.get("familia", "").strip().upper()
    state = request.query_params.get("estado", "TODOS").strip().upper()
    restock = request.query_params.get("reposicion", "") == "1"
    from_text, to_text = request.query_params.get("stock_desde", "").strip(), request.query_params.get("stock_hasta", "").strip()
    minimum, maximum = _decimal_filter(from_text), _decimal_filter(to_text)
    company_rows = [row for row in all_rows if row.product.empresa.codigo == company_code]
    rows = [row for row in company_rows if
        (not search or search.casefold() in row.product.sku.casefold() or search.casefold() in row.product.nombre.casefold())
        and (not family or (row.product.familia or "").upper() == family)
        and (state == "TODOS" or row.stock_state == state)
        and (not restock or row.requires_restock)
        and (minimum is None or row.displayed_stock >= minimum)
        and (maximum is None or row.displayed_stock <= maximum)]
    rows.sort(key=lambda row: product_natural_key(row.product))
    return templates.TemplateResponse(request=request, name="inventory/stock.html", context=context(
        rows=rows, company_code=company_code, mode=mode, transition=mode == MODE_TRANSITION,
        families=sorted({row.product.familia for row in company_rows if row.product.familia}),
        search=search, selected_family=family, selected_state=state, selected_restock=restock,
        stock_from=from_text, stock_to=to_text,
        active_page=f"inventory_stock_{company_code.lower()}", page_title=f"Stock {company_code}",
    ))


@router.get("/stock/boliklor", response_class=HTMLResponse, name="inventory_stock_boliklor")
def stock_boliklor(request: Request, db: Session = Depends(get_db)):
    return _stock_page(request, db, "BOLIKLOR")


@router.get("/stock/alm", response_class=HTMLResponse, name="inventory_stock_alm")
def stock_alm(request: Request, db: Session = Depends(get_db)):
    return _stock_page(request, db, "ALM")


@router.get("/inicializacion", response_class=HTMLResponse, name="inventory_initialization")
def initialization(request: Request, db: Session = Depends(get_db)):
    mode, rows = inventory_stock_rows(db)
    company = request.query_params.get("empresa", "").strip().upper()
    family = request.query_params.get("familia", "").strip().upper()
    search = request.query_params.get("q", "").strip()
    company_rows = [row for row in rows if not company or row.product.empresa.codigo == company]
    visible = [row for row in company_rows if
        (not family or (row.product.familia or "").upper() == family)
        and (not search or search.casefold() in row.product.sku.casefold() or search.casefold() in row.product.nombre.casefold())]
    return templates.TemplateResponse(request=request, name="inventory/initialization.html", context=context(
        rows=visible, mode=mode, companies=sorted({row.product.empresa.codigo for row in rows}),
        families=sorted({row.product.familia for row in company_rows if row.product.familia}),
        selected_company=company, selected_family=family, search=search,
        active_page="inventory_initialization", page_title="Inicialización de inventario",
    ))


@router.get("/costos", response_class=HTMLResponse, name="inventory_costs")
def inventory_costs(request: Request, db: Session = Depends(get_db)):
    mode, _ = inventory_stock_rows(db)
    return templates.TemplateResponse(request=request, name="inventory/costs.html", context=context(
        mode=mode, values=transactional_inventory_values(db),
        active_page="inventory_costs", page_title="Costo de inventario",
    ))
