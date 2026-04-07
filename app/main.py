from fastapi import FastAPI

from app.database import Base, engine
from app.routers import product, stock, warehouse

app = FastAPI(title="Shesha Warehouse System API")

# For initial scaffolding, auto-create tables at startup.
Base.metadata.create_all(bind=engine)

app.include_router(warehouse.router)
app.include_router(product.router)
app.include_router(stock.router)


@app.get("/health")
def health():
    return {"status": "ok"}
