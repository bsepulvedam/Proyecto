import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.orden_trabajo import OrdenTrabajoCreate, ProductoOT
from app.services.orden_trabajo_service import crear_orden


logger = logging.getLogger(__name__)
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="/ordenes-trabajo", tags=["web-ordenes-trabajo"])

ALLOWED_COMUNAS = ("Mostazal", "Colina")
INITIAL_PRODUCT_ROWS = 5
DEMO_USER = {"nombre": "Camila Soto", "rol": "Encargada de bodega"}


def work_order_dates(today: date | None = None) -> tuple[date, date]:
    request_date = today or date.today()
    return request_date, request_date + timedelta(days=2)


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def blank_product_row() -> dict[str, str]:
    return {"descripcion": "", "unidad": "", "cantidad": "", "medida_especifica": ""}


async def read_urlencoded_form(request: Request) -> dict[str, list[str]]:
    body = (await request.body()).decode("utf-8")
    return parse_qs(body, keep_blank_values=True, max_num_fields=500)


def first_value(form: dict[str, list[str]], name: str) -> str:
    return form.get(name, [""])[0].strip()


def extract_product_rows(form: dict[str, list[str]]) -> list[dict[str, str]]:
    fields = ("descripcion", "unidad", "cantidad", "medida_especifica")
    size = max((len(form.get(field, [])) for field in fields), default=0)
    return [
        {
            field: form[field][index].strip()
            if index < len(form.get(field, []))
            else ""
            for field in fields
        }
        for index in range(size)
    ]


def rows_for_form(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    visible_rows = [dict(row) for row in rows]
    while len(visible_rows) < INITIAL_PRODUCT_ROWS:
        visible_rows.append(blank_product_row())
    return visible_rows


def page_context(**values: object) -> dict[str, object]:
    request_date, delivery_date = work_order_dates()
    context: dict[str, object] = {
        "demo": {"usuario": DEMO_USER},
        "active_page": "work_orders",
        "page_title": "Nueva orden de trabajo",
        "page_eyebrow": "Órdenes de Trabajo",
        "allowed_comunas": ALLOWED_COMUNAS,
        "fecha_pedido": format_date(request_date),
        "fecha_entrega": format_date(delivery_date),
    }
    context.update(values)
    return context


def build_order(
    form: dict[str, list[str]],
) -> tuple[OrdenTrabajoCreate | None, list[str], list[dict[str, str]]]:
    comuna = first_value(form, "comuna")
    observations = first_value(form, "observaciones")
    raw_rows = extract_product_rows(form)
    errors: list[str] = []

    if comuna not in ALLOWED_COMUNAS:
        errors.append("Selecciona una comuna válida.")

    products: list[ProductoOT] = []
    has_used_row = False
    for index, row in enumerate(raw_rows, start=1):
        if not any(row.values()):
            continue
        has_used_row = True
        if not row["descripcion"] or not row["unidad"] or not row["cantidad"]:
            errors.append(
                f"La fila {index} está incompleta: descripción, UND. y cantidad son obligatorias."
            )
            continue
        try:
            quantity = Decimal(row["cantidad"])
        except InvalidOperation:
            errors.append(f"La cantidad de la fila {index} debe ser numérica.")
            continue
        if not quantity.is_finite() or quantity <= 0:
            errors.append(f"La cantidad de la fila {index} debe ser mayor que 0.")
            continue
        products.append(
            ProductoOT(
                descripcion=row["descripcion"],
                unidad=row["unidad"],
                cantidad=quantity,
                medida_especifica=row["medida_especifica"] or None,
            )
        )

    if not has_used_row:
        errors.append("Debes ingresar al menos un producto o detalle de trabajo válido.")

    if errors:
        return None, errors, raw_rows

    request_date, delivery_date = work_order_dates()
    try:
        order = OrdenTrabajoCreate(
            comuna=comuna,
            empresa_origen=None,
            recibe=None,
            fecha_pedido=request_date,
            fecha_entrega=delivery_date,
            fecha_finalizacion=None,
            estado=None,
            cliente=None,
            telefono=None,
            correo=None,
            recibido_por=None,
            lugar_trabajo=None,
            estado_cliente=None,
            referencia_pedido=None,
            responsable_boliklor=None,
            productos=products,
            observaciones=observations or None,
        )
    except ValidationError:
        logger.exception("Datos inválidos al construir la orden desde el formulario web")
        return None, ["Revisa los datos ingresados antes de continuar."], raw_rows
    return order, [], raw_rows


def order_to_context(order: OrdenTrabajoCreate) -> dict[str, object]:
    return {
        "order": order,
        "fecha_pedido": format_date(order.fecha_pedido),
        "fecha_entrega": format_date(order.fecha_entrega),
    }


@router.get("/nueva", response_class=HTMLResponse, name="new_work_order")
def new_work_order(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="work_orders/new.html",
        context=page_context(
            selected_comuna="",
            product_rows=rows_for_form([]),
            observaciones="",
            errors=[],
        ),
    )


@router.post("/nueva", response_class=HTMLResponse, include_in_schema=False)
async def edit_work_order(request: Request) -> HTMLResponse:
    form = await read_urlencoded_form(request)
    return templates.TemplateResponse(
        request=request,
        name="work_orders/new.html",
        context=page_context(
            selected_comuna=first_value(form, "comuna"),
            product_rows=rows_for_form(extract_product_rows(form)),
            observaciones=first_value(form, "observaciones"),
            errors=[],
        ),
    )


@router.post("/revisar", response_class=HTMLResponse, name="review_work_order")
async def review_work_order(request: Request) -> HTMLResponse:
    form = await read_urlencoded_form(request)
    order, errors, rows = build_order(form)
    if order is None:
        return templates.TemplateResponse(
            request=request,
            name="work_orders/new.html",
            context=page_context(
                selected_comuna=first_value(form, "comuna"),
                product_rows=rows_for_form(rows),
                observaciones=first_value(form, "observaciones"),
                errors=errors,
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return templates.TemplateResponse(
        request=request,
        name="work_orders/review.html",
        context=page_context(**order_to_context(order), error=None),
    )


@router.post("/confirmar", response_class=HTMLResponse, name="confirm_work_order")
async def confirm_work_order(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    form = await read_urlencoded_form(request)
    order, errors, rows = build_order(form)
    if order is None:
        return templates.TemplateResponse(
            request=request,
            name="work_orders/new.html",
            context=page_context(
                selected_comuna=first_value(form, "comuna"),
                product_rows=rows_for_form(rows),
                observaciones=first_value(form, "observaciones"),
                errors=errors,
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        created_order = crear_orden(db, order)
    except Exception:
        logger.exception("No fue posible confirmar la orden de trabajo desde la web")
        return templates.TemplateResponse(
            request=request,
            name="work_orders/review.html",
            context=page_context(
                **order_to_context(order),
                error="No fue posible crear la orden de trabajo. Intenta nuevamente.",
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return templates.TemplateResponse(
        request=request,
        name="work_orders/success.html",
        context=page_context(created_order=created_order),
        status_code=status.HTTP_201_CREATED,
    )
