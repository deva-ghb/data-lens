# Data Lens

Data Lens helps a container terminal decide, before each shift, who should do which job, and spot trouble while there is still time to act.
It was built for Health Challenge 06 as a working prototype for a fictional terminal, Mirsal Terminals in Abu Dhabi.
Every person, place and number in it is synthetic.

## What is here

- `working-prototype/` is the product: a Python backend, a React frontend, a seeded SQLite database, tests, and the demo video's recording scripts.
  Its own README explains how to run it, the sign-in accounts and how to reset the story.
- `large-version.txt` and `small-version.md` are the concept documents the prototype was built from.
- `user-capabliites.txt` is the role sheet: what each person sees and decides.

## Quick start

```sh
cd working-prototype
# backend
cd backend && uv run uvicorn app.main:app --port 8000
# frontend, in a second terminal
cd frontend && npm install && npx vite --port 5173
```

Open http://localhost:5173 and sign in as any `firstname.lastname@mirsalterminals.com` with the password `welcome@123`.
The copilot needs Azure OpenAI settings in `working-prototype/.env`; without them the app still runs and says the copilot is unavailable.
