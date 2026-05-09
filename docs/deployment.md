# Deployment Guide

DenialFighter deploys as two Railway services from the same GitHub repo.

---

## Prerequisites

- GitHub account with the repo pushed to `https://github.com/dheeerajpratap/Denialfighter`
- Railway account at [railway.app](https://railway.app)
- Groq API key from [console.groq.com](https://console.groq.com)

---

## Service 1: MCP Backend

### 1. Create Railway project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Select **Deploy from GitHub repo**
3. Authorize Railway and select `dheeerajpratap/Denialfighter`
4. Root directory: `/` (leave blank — uses root `railway.toml`)

Railway uses NIXPACKS to auto-detect Python and installs from `requirements.txt`.

### 2. Set environment variables

In Railway dashboard → your service → **Variables**:

| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` (already set in railway.toml) |

### 3. Self-reference URL (automatic)

Railway automatically injects `RAILWAY_PUBLIC_DOMAIN` into every deployment. The server uses this to resolve internal FHIR tool calls in production — **no manual `MCP_BASE_URL` needed**.

Your live MCP backend URL is:
```
https://denialfighter-production.up.railway.app
```

### 4. Verify deployment

```bash
curl https://denialfighter-production.up.railway.app/health
# {"status": "ok", "service": "DenialFighter MCP FHIR Reader"}

curl https://denialfighter-production.up.railway.app/.well-known/mcp.json
# Returns MCP manifest with 5 tools

curl https://denialfighter-production.up.railway.app/.well-known/agent.json
# Returns A2A agent card
```

---

## Service 2: Demo UI

### 1. Add a new service in the same Railway project

In your Railway project → **New** → **GitHub repo** → same repo `dheeerajpratap/Denialfighter`

Set **Root Directory** = `demo_ui`

Railway picks up `demo_ui/railway.toml`:
```toml
[build]
builder = "NIXPACKS"
buildCommand = "npm install && npm run build"

[deploy]
startCommand = "npx serve dist --listen $PORT"
```

### 2. Set build-time environment variable

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://denialfighter-production.up.railway.app` |

> **Important:** `VITE_API_URL` must be set **before** the build runs. Vite replaces `import.meta.env.VITE_API_URL` at build time, not runtime. If you change it, trigger a redeploy.

### 3. Verify

Open your UI Railway URL in a browser. The app should load and be able to reach the backend.

---

## Auto-Deploy on Push

Railway automatically redeploys both services when you push to the `main` branch on GitHub. No manual steps needed after initial setup.

---

## Environment Variables Summary

### MCP Backend (root service)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `FHIR_BASE_URL` | No | `https://hapi.fhir.org/baseR4` | FHIR server URL |
| `MCP_BASE_URL` | No | Auto from `RAILWAY_PUBLIC_DOMAIN` | Override only if needed |
| `PORT` | Auto | 8080 | Set by Railway |

### Demo UI (demo_ui service)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes (prod) | MCP backend Railway URL |
| `VITE_PAYER_API_URL` | No | Payer mock URL (optional) |

---

## Procfile

The `Procfile` at the repo root is used as a fallback start command:

```
web: uvicorn mcp_server.main:app --host 0.0.0.0 --port $PORT --workers 2
```

`railway.toml` takes precedence and uses the same command.

---

## Troubleshooting

**Build fails — module not found**
- Check `requirements.txt` has all dependencies
- Railway uses Python 3.11 by default — verify locally with `python --version`

**FHIR tools return 500**
- HAPI public test server occasionally times out; retry the request
- Check Railway logs: dashboard → service → **Logs**

**Pipeline never completes**
- `GROQ_API_KEY` not set → check Variables in Railway dashboard
- `MCP_BASE_URL` pointing to localhost → set it to your Railway URL

**UI shows "Network Error"**
- `VITE_API_URL` was set after build → trigger a manual redeploy in Railway
- CORS issue → the backend has `allow_origins=["*"]` so this should not happen

**Railway URL not assigned yet**
- Railway assigns a URL after the first successful deploy
- Go to service → **Settings** → **Domains** to find or generate it

---

## Local Development

Run all services simultaneously:

```bash
# Terminal 1 — MCP server
uvicorn mcp_server.main:app --reload --port 8000

# Terminal 2 — Payer mock
uvicorn payer_mock.main:app --port 8001

# Terminal 3 — Demo UI
cd demo_ui && npm run dev
```

Load FHIR test data once:
```bash
python scripts/load_fhir.py
```
