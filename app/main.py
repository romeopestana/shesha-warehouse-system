from fastapi import FastAPI

from app.routers import alerts, auth, jobs, notifications, product, reorder, stock, transfer, ui, warehouse

app = FastAPI(title="Shesha Warehouse System API")

app.include_router(auth.router)
app.include_router(warehouse.router)
app.include_router(product.router)
app.include_router(stock.router)
app.include_router(transfer.router)
app.include_router(alerts.router)
app.include_router(reorder.router)
app.include_router(notifications.router)
app.include_router(jobs.router)
app.include_router(ui.router)


@app.get("/health")
def health():
    return {"status": "ok"}
