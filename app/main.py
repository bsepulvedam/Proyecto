from fastapi import FastAPI

from app.api.ordenes import router as ordenes_router


app = FastAPI(title="Boliklor OT API", version="0.1.0")
app.include_router(ordenes_router)


@app.get("/")
def inicio() -> dict[str, bool | str]:
    return {"ok": True, "mensaje": "API Boliklor OT funcionando"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
