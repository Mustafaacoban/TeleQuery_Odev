from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import regions, packages, customers, subscriptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TeleQuery API",
    description="Telekomünikasyon müşteri ve abonelik yönetim sistemi.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(regions.router)
app.include_router(packages.router)
app.include_router(customers.router)
app.include_router(subscriptions.router)


@app.get("/", tags=["Genel"])
def root():
    return {"message": "TeleQuery API çalışıyor.", "docs": "/docs"}
