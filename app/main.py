from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import alerts, auth, notifications, product, stock, transfer, ui, warehouse

app = FastAPI(title="Shesha Warehouse System API")
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth.router)
app.include_router(warehouse.router)
app.include_router(product.router)
app.include_router(stock.router)
app.include_router(transfer.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(ui.router)


@app.get("/health")
def health():
    return {"status": "ok"}
