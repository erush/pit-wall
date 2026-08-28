# Deployment

Pit Wall supports a single-origin production deployment.

The React frontend is built with Vite and served by the FastAPI application.

## Production Architecture

```text
ChatGPT / Browser
        │
        ▼
 Public HTTPS Origin
        │
        ▼
      FastAPI
      │     │
      │     └── React Production Build
      │
      └── Pit Wall API
              │
              ▼
        Pit Wall Adapter
              │
              ▼
        Simulation Engine
```

Using one origin keeps the browser, API, and WebMCP-enabled page within the same deployed application.

## Requirements

- Python 3.11+
- Node.js
- npm

## Frontend Build

Install dependencies:

```bash
npm install
```

Build production assets:

```bash
npm run build
```

Vite writes the production application to:

```text
dist/
```

## Python Environment

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Local Production Server

Run FastAPI:

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Health Check

Endpoint:

```text
GET /health
```

Expected response:

```json
{
  "status": "healthy"
}
```

## API

Pit Wall API routes are mounted beneath:

```text
/api/v1/nascar
```

The standalone API includes only the functionality required by Pit Wall.

## Environment Variables

### `PITWALL_CORS_ORIGINS`

Optional comma-separated list of allowed origins.

### `PITWALL_CORS_ALLOW_CREDENTIALS`

Optional boolean controlling CORS credentials.

Default:

```text
false
```

### `RENDER_EXTERNAL_URL`

Render supplies this value in production.

Pit Wall automatically includes the Render external URL in its allowed origins.

## Docker

The repository includes a production `Dockerfile`.

The deployment process should:

1. install frontend dependencies
2. build the Vite application
3. install Python dependencies
4. start FastAPI/Uvicorn
5. bind to the platform-provided port

## Render

The repository includes `render.yaml` for Render deployment.

The service should:

- build from the repository Dockerfile
- bind to `0.0.0.0`
- use the `PORT` environment variable
- expose the application through public HTTPS

## WebMCP

WebMCP tools are registered client-side by the Pit Wall browser application.

No separate WebMCP server is required.

The deployed HTTPS application can be opened in a WebMCP-capable ChatGPT browser or compatible Chrome environment.

## Standalone Runtime

Production does not require:

- DuckDB
- NASCAR warehouse files
- raw NASCAR datasets
- DFS inputs
- generated analytics outputs
- the original NASCAR Decision Engine repository

All runtime components required by Pit Wall are contained in this repository.