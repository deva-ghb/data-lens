# Azure deployments used by Data Lens

Checked on 15 November 2026 against the endpoint in the project `.env` (host and key not recorded here).

| Deployment | Used for |
|---|---|
| `gpt-6-luna` | Written drafts through the Responses API with JSON-schema output (briefs, warning-record sections, incident records, learning items, translations, answers) |
| `gpt-6-luna` | Typed answers through the Decisions API (`POST /openai/v1/decisions`): incident triage, 5 by 5 risk scores, the question boundary, feed column mapping, inspection notes |
| `gpt-5.6-luna`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-4.1-mini` | Available, not used |

No image-generation deployment is used.
Settings: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` in `.env`; the app derives the `/openai/v1` base from the endpoint.
The project `.env` takes priority over variables exported in the shell.
