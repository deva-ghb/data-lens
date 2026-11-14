# Data Lens working prototype

This folder holds the Data Lens prototype for Mirsal Terminals.
The backend is a FastAPI service with a SQLite database.
The frontend is a React and TypeScript app built with Vite.

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

## Run the frontend

Install Node.js first (version 22 or newer).
Then run these commands:

```
cd frontend
npm install
npm run dev
```

The app opens at http://localhost:5173.
The dev server sends every request that starts with `/api` to the backend on port 8000, so start the backend too.
The home page calls `/api/health` and shows the status it returns.

## Run both together

From this folder, run `./start.sh`.
It starts the backend on port 8000 and the frontend on port 5173.
It installs the frontend packages the first time if they are missing.
Press Ctrl+C once to stop both.

## Settings

Settings are read from the environment and from the root `.env` file.
`DATALENS_JWT_SECRET` sets the secret used to sign login tokens.
If it is not set, a random secret is generated on first run and kept in `backend/data/.secret`, which git ignores.
The session cookie is `dl_session`, valid for 12 hours.
`DATABASE_URL` defaults to `sqlite:///data/datalens.db`, relative to the `backend` folder.

## Tests and checks

```
cd backend
uv run pytest
uv run ruff check .
```

Frontend checks:

```
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

## Database migrations

```
cd backend
uv run alembic upgrade head
```
