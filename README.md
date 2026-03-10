# ITC Classroom Finder — Agent Service

FastAPI + LangGraph agent that helps Dartmouth professors find teaching spaces. The frontend calls this service directly for the chat page.

## Setup

**Prerequisites** — assumed installed and available on your `PATH`:

| Tool | Version | Command |
|---|---|---|
| Python | 3.11.x | `python` |
| pip | bundled with Python | `pip` |

**Required environment variables** (put in `.env`):

| Variable | Description |
|---|---|
| `DARTMOUTH_CHAT_API_KEY` | Dartmouth Chat API key (used by `langchain_dartmouth`) |
| `DATABASE_URL` | Postgres transaction pooler connection string |
| `GOOGLE_MAPS_API_KEY` | Used for distance/address tools |
| `OPENAI_API_KEY` | Only needed if swapping the model to an OpenAI one |
| `PORT` | Agent service port (default: `8000`) |

```bash
pip install -r requirements.txt
```

## Running

| Mode | Command | Use for |
|---|---|---|
| Production | `python app.py` | Frontend calls `POST /chat` |
| CLI test | `python agent.py` | Manual testing in terminal |
| LangGraph Studio | `langgraph dev` | Visual graph debugging |

## Architecture Notes

### Model (`utils/model.py`)
Uses `ChatDartmouth` from `langchain_dartmouth`. The API key must be set or the app raises on import.

### Agent (`agent.py`)
Built with `create_agent` (LangGraph ReAct loop). The system prompt is defined here — it controls:
- When to call which tool (e.g., always expand acronyms before distance calls)
- When NOT to route to contacts (e.g., if no classrooms found, relax filters first)
- Response formatting rules (never produce classroom tables; the UI renders cards)

### Database (`utils/db.py`)
Direct Postgres connection via `psycopg2` with `RealDictCursor`. The agent queries the DB directly — no HTTP round-trip. The implementation assumes Postgres; swapping to another relational DB is possible but requires updating the connection logic in `db.py` and any raw SQL that uses Postgres-specific syntax.

### Tools

#### Classroom Queries (`utils/tools/queries.py`)
Both tools use `response_format="content_and_artifact"` — the text part goes to the LLM, the artifact (list of classroom dicts) is passed through to the frontend as structured JSON for card rendering.

**`query_classrooms_basic`** — filters by style (seminar/lecture/group learning) and seat count.  
**`query_classrooms_with_amenities`** — same as basic plus 15+ amenity filters (projector, Zoom, whiteboard, AC, etc.).

Both apply progressive fallback if no results:
1. Try all requested filters
2. Drop amenity filters, keep style + size
3. Drop style, keep size only ← capacity is non-negotiable
4. Return empty with a message to ask for different criteria

**`find_acronyms`** — string-replaces known Dartmouth building acronyms (HOP, ECSC, FOCO, etc.) with full names before passing to address/distance tools. Must be called first whenever acronyms appear in location queries.

#### Location (`utils/tools/location.py`)
Uses the Google Maps Geocoding and Distance Matrix APIs.

- **`validate_address`** — geocodes an address and confirms it exists before running distance queries.
- **`get_distance`** — returns walking distance/time between two addresses.
- **`sort_classrooms_by_distance`** — takes a list of classrooms and a reference location, returns them sorted by walking distance.

#### Contacts (`utils/tools/contacts.py`)
Keyword-based routing to Dartmouth offices (Registrar, Classroom Tech Services, etc.). Contact data and routing rules live in `contacts_config.yaml` — update that file to add/change offices without touching code.