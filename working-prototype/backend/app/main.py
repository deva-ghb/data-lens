from fastapi import APIRouter, FastAPI

from app.api.actions import router as actions_router
from app.api.activities import router as activities_router
from app.api.admin import router as admin_router
from app.api.assignments import router as assignments_router
from app.api.governance import router as governance_router
from app.api.home import router as home_router
from app.api.incidents import router as incidents_router
from app.api.ingest import router as ingest_router
from app.api.permits import router as permits_router
from app.api.warnings import router as warnings_router
from app.auth.router import router as auth_router
from app.errors import install_error_handlers

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(ingest_router)
api.include_router(home_router)
api.include_router(assignments_router)
api.include_router(activities_router)
api.include_router(governance_router)
api.include_router(permits_router)
api.include_router(warnings_router)
api.include_router(incidents_router)
api.include_router(actions_router)
api.include_router(admin_router)


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Data Lens")
install_error_handlers(app)
app.include_router(api)
