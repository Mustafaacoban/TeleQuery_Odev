from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import init_db
from app.routers import regions, packages, customers, subscriptions
from app.routers import employees, invoices, payments, support_tickets


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
app.include_router(employees.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(support_tickets.router)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", tags=["Genel"])
def root():
    return {"message": "TeleQuery API çalışıyor.", "docs": "/docs", "ui": "/ui"}


@app.get("/ui", include_in_schema=False)
def serve_ui():
    return FileResponse("app/static/index.html")
