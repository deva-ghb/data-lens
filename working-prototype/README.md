# Data Lens working prototype

This folder holds the Data Lens prototype for Mirsal Terminals.
The backend is a FastAPI service with a SQLite database.

## Run the backend

Install uv first if you do not have it (`brew install uv`).
Put `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in a `.env` file at this folder's root.
The endpoint is the full chat-completions URL.
The `.env` file is git-ignored and must never be committed.
Then run these commands:

```
cd backend
uv sync
uv run uvicorn app.main:app --port 8000
```

Check that it works at http://localhost:8000/api/health, which returns `{"status": "ok"}`.

## Settings

Settings are read from the environment and from the root `.env` file.
`DATALENS_JWT_SECRET` sets the secret used to sign login tokens.
If it is not set, a fixed development default is used, which is fine for a local prototype only.
`DATABASE_URL` defaults to `sqlite:///data/datalens.db`, relative to the `backend` folder.

## Tests and checks

```
cd backend
uv run pytest
uv run ruff check .
```

## Database migrations

```
cd backend
uv run alembic upgrade head
```
