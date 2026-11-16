"""Main FastAPI application entrypoint."""

from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.collector import router as collector_router
from app.routes.dashboard import router as dashboard_router
from app.routes.devices import router as devices_router
from app.routes.heart_rate import router as heart_rate_router
from app.routes.ingest import router as ingest_router
from app.routes.live import router as live_router
from app.routes.recovery import router as recovery_router
from app.routes.sleep import router as sleep_router
from app.routes.strain import router as strain_router
from app.routes.workouts import router as workouts_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(live_router)
app.include_router(ingest_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(heart_rate_router, prefix=settings.API_V1_PREFIX)
app.include_router(recovery_router, prefix=settings.API_V1_PREFIX)
app.include_router(strain_router, prefix=settings.API_V1_PREFIX)
app.include_router(sleep_router, prefix=settings.API_V1_PREFIX)
app.include_router(workouts_router, prefix=settings.API_V1_PREFIX)
app.include_router(devices_router, prefix=settings.API_V1_PREFIX)
app.include_router(collector_router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
async def health_check() -> dict:
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
