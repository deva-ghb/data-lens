from fastapi import APIRouter, FastAPI

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Data Lens")
app.include_router(api)
