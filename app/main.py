from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.devices import router as devices_router
from app.routers.location import router as location_router
from app.routers.history import router as history_router
from app.routers.sync import router as sync_router
from app.services.auto_sync import start_auto_sync_tasks


def create_app() -> FastAPI:
    app = FastAPI(title="CityTag Tracking Dashboard API")

    # CORS for local development – adjust origins as needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(devices_router)
    app.include_router(location_router)
    app.include_router(history_router)
    app.include_router(sync_router)
    start_auto_sync_tasks(app)
    

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

