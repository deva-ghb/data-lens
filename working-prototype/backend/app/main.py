from fastapi import APIRouter, FastAPI

from app.api.assignments import router as assignments_router
from app.api.home import router as home_router
from app.api.ingest import router as ingest_router
from app.auth.router import router as auth_router
from app.errors import install_error_handlers

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(ingest_router)
api.include_router(home_router)
api.include_router(assignments_router)


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Data Lens")
install_error_handlers(app)
app.include_router(api)
