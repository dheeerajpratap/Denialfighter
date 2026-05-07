# DenialFighter

**Prior Authorization Denial Appeal Agent | Agents Assemble Hackathon 2025**

> Payers use AI to deny faster. DenialFighter gives that power back to providers.

## What it does

When a prior authorization is denied, DenialFighter:
1. Reads the denial letter (extracts structured data via Agent 1 — Groq LLaMA 3.3)
2. Pulls the patient FHIR chart via MCP tools (medications, labs, conditions, history)
3. Matches clinical evidence to each denial reason using AI reasoning (Agent 2 — Groq LLaMA 3.3)
4. Writes a complete, formatted appeal letter with clinical citations (Agent 3 — Groq LLaMA 3.3)
5. Submits to payer API and creates a 30-day follow-up task

**Result:** 4-hour manual process → under 90 seconds

## Architecture

```
FHIR Data (HAPI) + Denial Letter
          ↓
    [MCP FHIR Reader Tool]          ← Published on Prompt Opinion Marketplace
    5 tools: patient, meds,
    conditions, labs, history
          ↓
    [/run-appeal REST API]          ← Called by Demo UI (async + polling)
          ↓
    [Agent 1: Denial Intake]        ← Groq LLaMA 3.3-70b — extracts structured data
          ↓
    [Agent 2: Evidence Match]       ← Groq LLaMA 3.3-70b — finds FHIR evidence
          ↓
    [Agent 3: Appeal Draft]         ← Groq LLaMA 3.3-70b — writes appeal letter
          ↓
    [Payer API Submission]
    + Follow-up task created
```

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (from console.groq.com)

# 3. Load FHIR data to HAPI test server
python scripts/load_fhir.py

# 4. Start MCP server + pipeline API (terminal 1)
uvicorn mcp_server.main:app --reload --port 8000

# 5. Start payer mock API (terminal 2)
uvicorn payer_mock.main:app --port 8001

# 6. Start demo UI (terminal 3)
cd demo_ui && npm install && npm run dev

# 7. Run CLI pipeline (optional — terminal 4)
python scripts/run_pipeline.py
```

## Environment variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key from console.groq.com |
| `FHIR_BASE_URL` | HAPI FHIR server (default: public test) |
| `MCP_BASE_URL` | MCP server URL (localhost:8000 for dev) |
| `PAYER_API_URL` | Payer mock URL (localhost:8001 for dev) |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/.well-known/mcp.json` | MCP manifest |
| POST | `/run-appeal` | Start pipeline (async) — returns `job_id` |
| GET | `/appeal-status/{job_id}` | Poll pipeline progress & results |
| POST | `/tools/get_patient_summary` | FHIR patient data |
| POST | `/tools/get_active_medications` | FHIR medications |
| POST | `/tools/get_conditions` | FHIR diagnoses |
| POST | `/tools/get_diagnostic_reports` | FHIR lab results |
| POST | `/tools/get_medication_history` | FHIR medication history |

## Running tests

```bash
# Unit tests (no servers needed)
pytest tests/test_agents.py -v

# Integration tests (requires MCP server + FHIR data loaded)
pytest tests/test_mcp.py tests/test_e2e.py -v -s

# Full suite
pytest tests/ -v
```

## Deployment (Railway)

```bash
# Deploy MCP server
railway up
# Set GROQ_API_KEY in Railway dashboard under Variables
```

MCP manifest URL after deploy: `https://your-app.railway.app/.well-known/mcp.json`

## Built with

Python · FastAPI · Groq (LLaMA 3.3-70b) · FHIR R4 · HAPI FHIR ·
MCP · A2A · Prompt Opinion · Railway · React · Vite

---

*"Payers use AI to deny. We use AI to fight back."*
