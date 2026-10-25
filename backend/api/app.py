"""
HealSense Backend API - Main Application Entry Point
FastAPI-based REST API for health monitoring and prediction
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime, timezone
import logging

from api.config import get_settings
from api.utils.logger import setup_logger
from api.routes import patients, alerts, devices, telemetry
from api.routes import realtime
from api.routes import ai
from api.routes import auth

# Initialize settings
settings = get_settings()

# Setup logging
logger = setup_logger()

from api.services.prediction_service import prediction_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting HealSense API...")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Initialize PredictionService
    try:
        if prediction_service.load_artifacts():
            logger.info("✅ ML prediction service initialized.")
        else:
            logger.warning("⚠️ Failed to load ML model. Running with clinical rules only.")
    except Exception as e:
        logger.error(f"❌ Error loading ML model: {e}")
    
    # TODO: Initialize database connection
    # TODO: Connect to Redis
    # TODO: Start MQTT client
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down HealSense API...")
    # TODO: Close database connections
    # TODO: Cleanup resources

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Health Monitoring & Risk Prediction System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

class UnhandledExceptionMiddleware:
    """Return sanitized HTTP errors inside CORS, before a response starts."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def tracked_send(message: Message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception:
            if response_started:
                raise
            logger.exception("Unhandled HTTP request error")
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": "internal_error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await response(scope, receive, send)


# Last registered user middleware is outermost: errors must pass through CORS.
app.add_middleware(UnhandledExceptionMiddleware)
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Add rate limiting middleware
# TODO: Add authentication middleware

# Include routers
app.include_router(telemetry.router, prefix=f"{settings.API_V1_PREFIX}/telemetry", tags=["Telemetry Ingestion"])
app.include_router(patients.router, prefix=f"{settings.API_V1_PREFIX}/patients", tags=["Patients"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"])
app.include_router(devices.router, prefix=f"{settings.API_V1_PREFIX}/devices", tags=["Devices"])
app.include_router(ai.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(realtime.router, tags=["Realtime"])

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENV
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to HealSense API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "health": "/health",
        "realtime": {
            "live": "/ws/live",
            "patient": "/ws/patients/{patient_id}",
            "device": "/ws/devices/{device_id}"
        },
        "endpoints": {
            "auth": f"{settings.API_V1_PREFIX}/auth",
            "patients": f"{settings.API_V1_PREFIX}/patients",
            "data": f"{settings.API_V1_PREFIX}/data",
            "predict": f"{settings.API_V1_PREFIX}/predict",
            "analytics": f"{settings.API_V1_PREFIX}/analytics",
            "ai": f"{settings.API_V1_PREFIX}/ai"
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# 404 handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content=(exc.detail if isinstance(exc.detail, dict) else {
            "detail": "Resource not found",
            "path": str(request.url),
            "timestamp": datetime.utcnow().isoformat()
        })
    )

# TODO: Include routers
# app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
# app.include_router(sensor_data.router, prefix=f"{settings.API_V1_PREFIX}/data", tags=["Sensor Data"])
# app.include_router(prediction.router, prefix=f"{settings.API_V1_PREFIX}/predict", tags=["Predictions"])
# app.include_router(patients.router, prefix=f"{settings.API_V1_PREFIX}/patients", tags=["Patients"])
# app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
