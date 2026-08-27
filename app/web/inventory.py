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
from app.services.inventario_catalogo_service import listar_empresas
from app.services.inventario_movimiento_service import InventoryMovementError, create_receipt, get_movement, list_movements

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


def money(value):
    return f"${int(value or 0):,}".replace(",", ".")


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
    return templates.TemplateResponse(request=request, name="inventory/movements.html", context=context(
        movements=list_movements(db), active_page="inventory_movements", page_title="Movimientos de inventario",
    ))


@router.get("/movimientos/{movement_id}", response_class=HTMLResponse, name="inventory_movement_detail")
def movement_detail(request: Request, movement_id: int, db: Session = Depends(get_db)):
    movement = get_movement(db, movement_id)
    if movement is None:
        return HTMLResponse("Movimiento no encontrado", status_code=404)
    return templates.TemplateResponse(request=request, name="inventory/movement_detail.html", context=context(
        movement=movement, active_page="inventory_movements", page_title=movement.numero_documento,
    ))
