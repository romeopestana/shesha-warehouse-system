from fastapi import FastAPI

from app.routers import auth, product, stock, warehouse

app = FastAPI(title="Shesha Warehouse System API")

app.include_router(auth.router)
app.include_router(warehouse.router)
app.include_router(product.router)
app.include_router(stock.router)


@app.get("/health")
def health():
    return {"status": "ok"}
