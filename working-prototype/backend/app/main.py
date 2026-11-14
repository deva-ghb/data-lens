from fastapi import APIRouter, FastAPI

from app.errors import install_error_handlers

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Data Lens")
install_error_handlers(app)
app.include_router(api)
