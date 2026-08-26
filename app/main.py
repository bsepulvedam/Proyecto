from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.ordenes import router as ordenes_router
from app.web.dashboard import router as dashboard_router
from app.web.work_orders import router as work_orders_router


app = FastAPI(title="Boliklor OT API", version="0.1.0")
app.include_router(ordenes_router)
app.include_router(dashboard_router)
app.include_router(work_orders_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def inicio() -> dict[str, bool | str]:
    return {"ok": True, "mensaje": "API Boliklor OT funcionando"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
