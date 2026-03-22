"""Monitoring endpoints: health check and metrics."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="", tags=["monitoring"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for liveness/readiness probes.

    Returns:
        Health status information
    """
    return HealthResponse(
        status="ok",
        service="SeeWorldWeb",
        version="1.0.0"
    )
