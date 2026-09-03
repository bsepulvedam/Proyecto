from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.ordenes import router as ordenes_router
from app.api.productos import router as productos_api_router
from app.web.dashboard import router as dashboard_router
from app.web.products import router as products_router
from app.web.work_orders import router as work_orders_router
from app.web.inventory import router as inventory_router
from app.web.auth import router as auth_router
from app.web.admin import router as admin_router
from app.web.attendance import router as attendance_router
from app.web.attendance_supervision import router as attendance_supervision_router
from app.web.attendance_rates import router as attendance_rates_router
from app.core.config import validate_security_config
from app.core.security import require_module, require_platform_access


validate_security_config()
app = FastAPI(title="Boliklor OT API", version="0.1.0")
app.include_router(auth_router)
app.include_router(admin_router, dependencies=[Depends(require_module("ADMIN_ACCESS"))])
app.include_router(attendance_rates_router, dependencies=[Depends(require_module("ADMIN_ACCESS"))])
app.include_router(attendance_router, dependencies=[Depends(require_module("ASISTENCIA_PROPIA"))])
app.include_router(attendance_supervision_router, dependencies=[Depends(require_module("ASISTENCIA_SUPERVISAR"))])
app.include_router(ordenes_router, dependencies=[Depends(require_module("OT_ACCESS"))])
app.include_router(productos_api_router, dependencies=[Depends(require_module("INVENTARIO_ACCESS"))])
app.include_router(dashboard_router, dependencies=[Depends(require_platform_access)])
app.include_router(work_orders_router, dependencies=[Depends(require_module("OT_ACCESS"))])
app.include_router(products_router, dependencies=[Depends(require_module("INVENTARIO_ACCESS"))])
app.include_router(inventory_router, dependencies=[Depends(require_module("INVENTARIO_ACCESS"))])
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def inicio() -> dict[str, bool | str]:
    return {"ok": True, "mensaje": "API Boliklor OT funcionando"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
