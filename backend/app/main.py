from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.database import Base, engine
import app.models  # noqa: F401  # register all models so create_all creates every table


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    # Start background scheduler
    from app.services.scheduler_service import (
        check_lead_timeout,
        check_task_due,
        check_payment_overdue,
    )
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_lead_timeout, "interval", hours=6, id="lead_timeout")
    scheduler.add_job(check_task_due, "interval", hours=1, id="task_due")
    scheduler.add_job(check_payment_overdue, "interval", hours=6, id="payment_overdue")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="CRM System",
    description="CRM System Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware (allow all origins in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Service is running normally"}
