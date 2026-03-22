import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from config import settings, __version__
from utils.logger import setup_logging, get_logger
from api.auth import router as auth_router
from api.monitoring import router as monitoring_router
from api.websocket import websocket_endpoint

# Setup logging before app initialization
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="SeeWorldWeb Backend", version=__version__)

# CORS configuration
origins = settings.cors_allow_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(monitoring_router)
app.add_api_websocket_route("/ws", websocket_endpoint)

# Add Prometheus instrumentation - exclude health and metrics endpoints to avoid self-monitoring
Instrumentator(
    excluded_handlers=["/health", "/metrics"]
).instrument(app).expose(app)

logger.info("Application started", routes=["/", "/health", "/metrics", "/auth/*", "/ws"])


@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"status": "ok", "service": "SeeWorldWeb", "version": __version__}


if __name__ == "__main__":
    logger.info(
        "Starting Uvicorn server",
        host=settings.host,
        port=settings.port,
        debug=settings.debug
    )
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
