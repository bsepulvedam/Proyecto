from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(tags=["web"])


# Datos temporales de demostracion. En esta fase no se consulta PostgreSQL.
DASHBOARD_DEMO = {
    "fecha": "Miércoles, 19 de agosto de 2026",
    "usuario": {"nombre": "Camila Soto", "rol": "Encargada de bodega"},
    "kpis": [
        {"label": "Productos registrados", "value": "248", "detail": "12 nuevos este mes", "icon": "bi-box-seam", "variant": ""},
        {"label": "Productos con stock bajo", "value": "14", "detail": "Requieren reposición", "icon": "bi-exclamation-triangle", "variant": "warning"},
        {"label": "Productos próximos a vencer", "value": "8", "detail": "En los próximos 30 días", "icon": "bi-calendar-x", "variant": "danger"},
        {"label": "Solicitudes pendientes", "value": "6", "detail": "2 con prioridad alta", "icon": "bi-clipboard-check", "variant": "info"},
        {"label": "Entradas de hoy", "value": "23", "detail": "156 unidades recibidas", "icon": "bi-box-arrow-in-down", "variant": "success"},
        {"label": "Salidas de hoy", "value": "17", "detail": "94 unidades entregadas", "icon": "bi-box-arrow-up", "variant": "neutral"},
    ],
    "productos_por_vencer": [
        {"codigo": "PIN-AMA-01", "producto": "Pintura amarilla alto tráfico", "lote": "LA-24081", "stock": "12 gal.", "fecha": "25/08/2026", "estado": "Vence pronto", "variant": "danger"},
        {"codigo": "PIN-BLA-04", "producto": "Pintura blanca exterior", "lote": "LB-11926", "stock": "8 gal.", "fecha": "02/09/2026", "estado": "Por vencer", "variant": "warning"},
        {"codigo": "ACR-TRA-02", "producto": "Acrílico transparente 5 mm", "lote": "AC-30514", "stock": "24 un.", "fecha": "10/09/2026", "estado": "Por vencer", "variant": "warning"},
        {"codigo": "SEN-REF-08", "producto": "Señalética reflectante", "lote": "SR-08211", "stock": "35 un.", "fecha": "17/09/2026", "estado": "En seguimiento", "variant": "info"},
    ],
    "solicitudes": [
        {"numero": "SOL-2026-084", "solicitante": "Diego Muñoz", "fecha": "19/08/2026", "productos": "5 productos", "estado": "Prioridad alta", "variant": "danger"},
        {"numero": "SOL-2026-081", "solicitante": "Paula Rojas", "fecha": "18/08/2026", "productos": "3 productos", "estado": "En revisión", "variant": "warning"},
        {"numero": "SOL-2026-079", "solicitante": "Matías Vera", "fecha": "18/08/2026", "productos": "7 productos", "estado": "Aprobada", "variant": "info"},
        {"numero": "SOL-2026-076", "solicitante": "Fernanda Silva", "fecha": "17/08/2026", "productos": "2 productos", "estado": "Pendiente", "variant": "neutral"},
    ],
}


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={"demo": DASHBOARD_DEMO},
    )
