from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.inventario_movimiento_service import list_movements
from app.services.inventory_stock_service import MODE_TRANSITION, inventory_stock_rows

templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
router = APIRouter(tags=["web"])
DEMO_USER = {"usuario": {"nombre": "Camila Soto", "rol": "Encargada de bodega"}}


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    mode, rows = inventory_stock_rows(db)
    all_movements = list_movements(db)
    kpis = [
        {"label": "Productos BOLIKLOR", "value": sum(row.product.empresa.codigo == "BOLIKLOR" for row in rows), "detail": "Catálogo maestro", "icon": "bi-box-seam", "variant": ""},
        {"label": "Productos ALM", "value": sum(row.product.empresa.codigo == "ALM" for row in rows), "detail": "Catálogo maestro", "icon": "bi-boxes", "variant": "info"},
        {"label": "Productos sin stock", "value": sum(row.displayed_stock <= 0 for row in rows), "detail": "Stock mostrado ≤ 0", "icon": "bi-x-circle", "variant": "danger"},
        {"label": "Bajo mínimo", "value": sum(row.requires_restock for row in rows), "detail": "Alerta auxiliar de reposición", "icon": "bi-exclamation-triangle", "variant": "warning"},
        {"label": "Movimientos registrados", "value": len(all_movements), "detail": "Motor transaccional PostgreSQL", "icon": "bi-arrow-left-right", "variant": "success"},
    ]
    return templates.TemplateResponse(request=request, name="dashboard/index.html", context={
        "demo": DEMO_USER, "today": date.today(), "mode": mode, "transition": mode == MODE_TRANSITION,
        "kpis": kpis, "movements": all_movements[:8], "active_page": "dashboard",
        "page_title": "Dashboard", "page_eyebrow": "Resumen general",
    })
