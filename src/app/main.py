"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.app.logging_config import setup_logging, get_logger
from src.app.config import settings
from src.app.api.webhooks import router as webhooks_router
from src.app.models.base import engine, Base

# Setup logging
setup_logging(debug=settings.debug)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AutoQA",
    description="Automated Quality Assurance for GitHub",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting AutoQA application")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        # Don't fail startup if tables already exist


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down AutoQA application")
    
    # Close database connections
    await engine.dispose()


# Include routers
app.include_router(webhooks_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AutoQA",
        "status": "running",
        "version": "1.0.0"
    }

