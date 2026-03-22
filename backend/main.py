import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.auth import router as auth_router
from api.websocket import websocket_endpoint

app = FastAPI(title="SeeWorldWeb Backend", version="1.0.0")

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
app.add_api_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    return {"status": "ok", "service": "SeeWorldWeb", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
