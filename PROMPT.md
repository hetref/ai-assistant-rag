## AI Contributor Prompt for Business Location RAG System

Use this document as the complete, self-sufficient context when building or extending features in this repository. It explains the architecture, data models, APIs, file conventions, coding standards, and provides example commands. Include it verbatim (or relevant excerpts) when prompting an AI to work on the project.

### Project Overview

The project is a Business Location System combining:
- Pathway RAG server for real-time document indexing, hybrid retrieval (vector + BM25), and QA APIs.
- FastAPI service for business registration, CSV storage, and location-based search over vectorized data.
- Streamlit UI for registration, search, and system status.

Primary goals:
- Register businesses with geocoordinates and metadata.
- Store each business as an individual JSON document under `data/businesses/` for better indexing.
- Provide AI-powered semantic search with location filtering and ranking.

### Architecture

- Pathway service (port 8000) defined by `app.py` and `app.yaml`.
- Upload/Search API (port 8001) defined in `upload_api.py`.
- Streamlit UI (port 8501) in `ui/main.py` (+ pages/ routes if enabled).
- Data storage directory: `data/`
  - CSV: `data/data.csv` (append-only log/storage)
  - Per-business documents: `data/businesses/*.json` (source of truth for indexing)

Data is ingested by Pathway from `data/businesses/` as binary files. The parser accepts JSON, a legacy key:value text format, or CSV-like lines embedded in documents for backward compatibility.

### Runtime and Commands

- Start Pathway + Upload API:
```bash
python app.py
```
- Start Streamlit UI:
```bash
streamlit run ui/main.py --server.port 8501
```
- With Docker:
```bash
docker compose up --build
```

### Key Files and Directories

- `app.py`: boots Pathway and also runs the Upload API (FastAPI) on 8001.
- `app.yaml`: Pathway configuration for sources, parser, splitter, indexes, and QA server.
- `upload_api.py`: FastAPI app for registration and search APIs. Writes CSV, maintains `businesses.txt`, and writes per-business JSON.
- `utils.py`: Helpers for distance calculation, parsing lat/long, filtering, and formatting.
- `ui/main.py`: Streamlit UI home page with links to registration, search, and RAG chat.
- `data/`: data directory (CSV, mirror TXT, and per-business JSON files).
- `scripts/convert_businesses_to_json.py`: Converts legacy per-business `.txt` to `.json` (non-destructive).
- `scripts/delete_txt_business_files.py`: Deletes only `.txt` files under `data/businesses/`.

### Data Model

Per-business JSON schema written by the API (source of truth):
```json
{
  "name": "Owner Name",              
  "owner_name": "Owner Name",       
  "business_name": "Business Name", 
  "business_category": "Cafe",      
  "business_tags": "coffee,wifi",   
  "latitude": 37.7749,               
  "longitude": -122.4194,            
  "lat_long": "37.7749,-122.4194"   
}
```

CSV row schema persisted to `data/data.csv` for historical reasons:
```csv
name,business_name,lat_long,business_category,business_tags
```

### API Endpoints (Upload/Search API on port 8001)

- POST `/append-csv`
  - Registers a single business. Validates coordinates. Appends to CSV, writes mirror to `businesses.txt`, and creates a per-business `.json` in `data/businesses/`.
  - Request:
```json
{
  "name": "John Smith",
  "business_name": "Smith Coffee House",
  "lat_long": "37.7749,-122.4194",
  "business_category": "Cafe",
  "business_tags": "coffee,wifi,outdoor-seating"
}
```
  - Response (200):
```json
{
  "ok": true,
  "appended": 1,
  "csv_path": "data/data.csv",
  "coordinates": {"latitude": 37.7749, "longitude": -122.4194}
}
```

- POST `/append-csv/batch`
  - Registers multiple businesses at once. Same validations and side-effects as above.
  - Request:
```json
{
  "records": [ { "name": "...", "business_name": "...", "lat_long": "...", "business_category": "...", "business_tags": "..." } ]
}
```

- POST `/search-businesses`
  - Vectorized semantic search via Pathway + location filtering and hybrid ranking.
  - Request:
```json
{
  "user_lat": 37.7749,
  "user_lng": -122.4194,
  "query": "coffee shops with wifi",
  "max_distance_km": 20.0,
  "category_filter": "Cafe",
  "tag_filters": ["wifi", "coffee"],
  "limit": 10,
  "distance_weight": 0.3,           
  "sort_mode": "hybrid"            
}
```

- GET `/health`
  - Returns API health plus connectivity to Pathway. Example:
```json
{
  "status": "healthy",
  "csv_exists": true,
  "csv_path": "data/data.csv",
  "data_dir": "data",
  "pathway_status": "online",
  "pathway_url": "http://localhost:8000"
}
```

### Pathway API (port 8000)

Core endpoints used by this system (see Pathway docs for full spec):
- POST `/v1/statistics` – system statistics/health.
- POST `/v2/list_documents` – lists documents/indexing status.
- POST `/v1/retrieve` – vector retrieval used by our search pipeline.

### Parsing and Indexing

The vectorized search retrieves chunks from Pathway. We parse businesses out of chunk text with `parse_business_from_text` (in `upload_api.py`). The parser supports:
- JSON objects or arrays (preferred)
- Legacy key:value lines
- CSV-like single lines

For new features, prefer writing and consuming JSON to and from `data/businesses/*.json`.

### Scripts

- Convert legacy `.txt` files to `.json` (non-destructive):
```bash
python scripts/convert_businesses_to_json.py
```

- Delete all `.txt` files from `data/businesses/`:
```bash
python scripts/delete_txt_business_files.py
```

### Environment

Key variables (see `docker-compose.yml` and `.env`):
- `OPENAI_API_KEY` (required for embeddings/LLM)
- `DATA_DIR` (default `data`)
- `PATHWAY_HOST` (default `localhost` or `0.0.0.0` in containers)
- `PATHWAY_PORT` (default `8000`)

### Coding Standards (follow when generating code)

- Python 3.11+. Keep code clear and highly readable.
- Use descriptive names (no 1–2 char names). Prefer full words.
- Functions: explicit arguments and return types where helpful.
- Control flow: early returns, handle errors and edge cases, avoid deep nesting.
- Comments: only where complexity requires context (explain “why”, not “how”).
- Formatting: match existing style; avoid unrelated refactors.
- Linting: ensure no new linter errors are introduced.

### Constraints and Conventions

- Business registration must always write per-business `.json` under `data/businesses/` and maintain CSV + mirror TXT for compatibility.
- Geo-coordinates must be validated: latitude in [-90, 90], longitude in [-180, 180].
- Distances computed with Haversine (`utils.calculate_distance`).
- Search ranking combines semantic score and distance; `distance_weight` and `sort_mode` can tune behavior.

### Test and Debug Examples

- Register a business:
```bash
curl -X POST http://localhost:8001/append-csv \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "business_name": "Smith Coffee House",
    "lat_long": "37.7749,-122.4194",
    "business_category": "Cafe",
    "business_tags": "coffee,wifi"
  }'
```

- Search businesses:
```bash
curl -X POST http://localhost:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194,
    "query": "coffee shop near me",
    "max_distance_km": 20.0,
    "category_filter": "Cafe",
    "tag_filters": ["wifi"],
    "limit": 10
  }'
```

- Pathway status:
```bash
curl -X POST http://localhost:8000/v1/statistics
```

### System Prompt Template for AI Contributors

Use the following as a base system prompt when asking the AI to implement new features:

```text
You are contributing to the Business Location RAG System. Follow these rules:
1) Maintain per-business JSON files under data/businesses/ when writing new records.
2) Never break existing APIs. If adding routes, follow FastAPI style in upload_api.py.
3) Preserve coordinate validation and distance logic in utils.py.
4) Ensure Pathway continues to read from data/businesses/ and parsing remains backward compatible.
5) Keep code highly readable, with descriptive names and minimal deep nesting.
6) Don’t introduce linter errors. Match existing formatting and structure.
7) Provide example curl commands for any new endpoints.
8) If creating scripts, default to safe, non-destructive behavior unless explicitly a cleanup.

Context:
- Upload/Search API on :8001 with endpoints: /append-csv, /append-csv/batch, /search-businesses, /health.
- Pathway API on :8000 with endpoints: /v1/statistics, /v2/list_documents, /v1/retrieve.
- Data directory: data/ with CSV, mirror TXT, and per-business JSON files. JSON schema:
  { name, owner_name, business_name, business_category, business_tags, latitude, longitude, lat_long }
- UI in Streamlit at :8501 (ui/main.py).

When implementing changes:
- Update documentation comments and add concise docstrings as needed.
- Verify inputs, handle errors gracefully, and return consistent JSON responses.
- Ensure any new files are placed in logical directories and imported correctly.
```

### Notes for Future Features

- If adding new attributes to businesses, ensure backward compatibility in the parser and update JSON writing accordingly.
- For new search facets, extend request models in `upload_api.py` and incorporate into vectorized retrieval and filtering phases.
- Consider adding indexing hints or metadata if needed by Pathway (e.g., to improve retrieval for new fields).


