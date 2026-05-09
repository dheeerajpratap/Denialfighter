# DenialFighter

> **Payers use AI to deny faster. DenialFighter gives that power back to providers.**

Prior authorization denials affect 93 million Americans annually. Appealing one takes a physician 4 hours. Fewer than 1% of denials are ever appealed — not because the case is weak, but because the process is broken. DenialFighter fixes that.

**4 hours → under 90 seconds. No compromise on quality.**

---

## What It Does

DenialFighter is an AI agent that reads a prior authorization denial letter, pulls the patient's clinical chart from a FHIR server, and produces a complete, evidence-backed appeal letter — ready to submit.

```
Insurance Denial Letter + Patient FHIR ID
             ↓
    ┌─────────────────────────┐
    │   MCP FHIR Reader       │  ← 5 tools published on Prompt Opinion
    │   (SHARP context)       │
    └────────────┬────────────┘
                 ↓
    ┌────────────────────────┐
    │  Agent 1: Denial Intake │  ← Groq LLaMA 3.3-70b
    │  Parses letter → JSON   │     Extracts: drug, reasons, deadline
    └────────────┬────────────┘
                 ↓
    ┌─────────────────────────┐
    │  Agent 2: Evidence Match │  ← Groq LLaMA 3.3-70b
    │  FHIR chart → evidence   │     Medical necessity score 0-100
    └────────────┬─────────────┘
                 ↓
    ┌─────────────────────────┐
    │  Agent 3: Appeal Draft   │  ← Groq LLaMA 3.3-70b
    │  Writes appeal letter    │     8-section, 600-750 words
    └────────────┬─────────────┘
                 ↓
    Complete Appeal Packet
    (letter + evidence + attachments checklist)
```

---

## Key Numbers

| Metric | Manual | DenialFighter |
|--------|--------|---------------|
| Time per appeal | ~4 hours | ~90 seconds |
| Appeals filed | <1% of denials | Every denial |
| Appeal reversal rate | 67% (when filed) | Targeting 70%+ |
| Evidence citations | Variable | 100% FHIR-sourced |

---

## Architecture

### MCP Server — 5 FHIR Tools

Published on the Prompt Opinion Marketplace. Any agent in the ecosystem can call these tools.

| Tool | FHIR Resource | Returns |
|------|---------------|---------|
| `get_patient_summary` | Patient + Coverage | Name, DOB, member ID, insurance plan |
| `get_active_medications` | MedicationRequest (active) | Current drugs, doses, prescribers |
| `get_conditions` | Condition | Diagnoses with ICD-10 codes |
| `get_diagnostic_reports` | DiagnosticReport | Lab results, pathology, imaging |
| `get_medication_history` | MedicationRequest (all) | Prior drugs + reasons stopped |

Every tool call receives FHIR context injected by Prompt Opinion via SHARP Extension Specs:
- `x-fhir-server-url` — which FHIR server to query
- `x-fhir-access-token` — auth token (when required)
- `x-patient-id` — patient in scope

### A2A Agent Pipeline

Three specialized agents chained in sequence, each with a distinct role:

**Agent 1 — Denial Intake** (`agents/denial_intake_agent.py`)
- Model: Groq LLaMA 3.3-70b-versatile, temperature 0
- Input: Free-text denial letter
- Output: Structured JSON — drug, denial reason codes, reference number, appeal deadline, missing docs, urgency level

**Agent 2 — Evidence Matching** (`agents/evidence_match_agent.py`)
- Model: Groq LLaMA 3.3-70b-versatile, temperature 0
- Input: Denial JSON + patient FHIR chart
- Output: Medical necessity score (0-100), appeal strength, evidence items, step therapy proof, NCCN guideline citations

**Agent 3 — Appeal Drafting** (`agents/appeal_draft_agent.py`)
- Model: Groq LLaMA 3.3-70b-versatile, temperature 0.1
- Input: Denial data + evidence summary + patient demographics
- Output: Complete appeal letter (600-750 words, 8 sections)

### Discovery Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /.well-known/mcp.json` | MCP manifest — tool schemas for marketplace |
| `GET /.well-known/agent.json` | A2A agent card — agent discovery |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key from [console.groq.com](https://console.groq.com)

### 1. Install dependencies

```bash
pip install -r requirements.txt
cd demo_ui && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

### 3. Load sample FHIR data

```bash
python scripts/load_fhir.py
# Loads Sarah Chen's patient bundle to HAPI public test server
# Prints the patient_id — default is 132011823
```

### 4. Start the MCP server

```bash
uvicorn mcp_server.main:app --reload --port 8000
```

### 5. Start the payer mock (optional, for end-to-end demo)

```bash
uvicorn payer_mock.main:app --port 8001
```

### 6. Start the demo UI

```bash
cd demo_ui && npm run dev
# Open http://localhost:5173
```

### 7. Run the CLI pipeline (optional)

```bash
python scripts/run_pipeline.py
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | From [console.groq.com](https://console.groq.com) |
| `FHIR_BASE_URL` | No | FHIR server base URL (default: HAPI public test server) |
| `MCP_BASE_URL` | No | MCP server URL (default: `http://localhost:8000`) |
| `PAYER_API_URL` | No | Payer mock URL (default: `http://localhost:8001`) |
| `PORT` | No | Server port — auto-set by Railway |

---

## API Reference

### Pipeline

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/run-appeal` | Start pipeline — returns `job_id` immediately |
| `GET` | `/appeal-status/{job_id}` | Poll progress and results |

**POST /run-appeal**
```json
{
  "patient_id": "132011823",
  "denial_letter": "MedAdvantage Premier Plan\nDate: April 15, 2025\n..."
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

**GET /appeal-status/{job_id} — completed**
```json
{
  "status": "done",
  "steps": [...],
  "result": {
    "appeal_letter": "Dear Appeals Department...",
    "medical_necessity_score": 92,
    "appeal_strength": "strong",
    "submission_ready": true,
    "processing_time_seconds": 87.3
  }
}
```

### FHIR Tools (MCP)

All tool endpoints accept `POST` with `{"patient_id": "..."}`. When called from Prompt Opinion, patient ID is injected via `x-patient-id` header.

| Endpoint | Returns |
|----------|---------|
| `POST /tools/get_patient_summary` | Patient demographics + insurance |
| `POST /tools/get_active_medications` | Active medications list |
| `POST /tools/get_conditions` | Diagnoses with ICD-10 codes |
| `POST /tools/get_diagnostic_reports` | Lab results and reports |
| `POST /tools/get_medication_history` | All medications including stopped |

### Discovery

| Endpoint | Returns |
|----------|---------|
| `GET /.well-known/mcp.json` | MCP tool manifest |
| `GET /.well-known/agent.json` | A2A agent card |
| `GET /health` | `{"status": "ok"}` |

---

## Running Tests

```bash
# Unit tests — no external services needed
pytest tests/test_agents.py -v

# Integration tests — requires MCP server running
pytest tests/test_mcp.py -v -s

# End-to-end tests — requires MCP server + FHIR data loaded
pytest tests/test_e2e.py -v -s

# Full suite
pytest tests/ -v
```

---

## Deployment

See [docs/deployment.md](docs/deployment.md) for full Railway deployment guide.

**Quick deploy:**
```bash
# Push to GitHub, then connect Railway to your repo
# Set GROQ_API_KEY in Railway dashboard
# Set MCP_BASE_URL to your Railway public URL
```

---

## Prompt Opinion Integration

See [docs/prompt-opinion-integration.md](docs/prompt-opinion-integration.md) for the full guide.

The MCP server publishes 5 FHIR tools to the Prompt Opinion Marketplace. After deploying to Railway:

1. Register at [app.promptopinion.ai](https://app.promptopinion.ai)
2. Publish MCP server using your Railway URL + `/.well-known/mcp.json`
3. Platform injects FHIR context via SHARP headers on every tool call

---

## Sample Case

**Patient:** Sarah Chen, 56F, Non-small cell lung cancer (C34.11)
**Denied drug:** Pembrolizumab 200mg IV q3weeks (J9271)
**Denial reasons:** Medical necessity, step therapy, missing documentation
**Pipeline result:** Score 92/100, appeal strength STRONG, letter generated in 87 seconds

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **AI:** Groq API — LLaMA 3.3-70b-versatile
- **FHIR:** FHIR R4, HAPI FHIR server
- **MCP:** Model Context Protocol, Prompt Opinion SHARP Extension Specs
- **A2A:** Agent-to-Agent protocol, Prompt Opinion Marketplace
- **Frontend:** React 18, Vite 5
- **Deployment:** Railway (NIXPACKS)

---

## Project Structure

```
Denialfighter/
├── agents/                    # AI agent implementations
│   ├── denial_intake_agent.py     # Agent 1 — parse denial letter
│   ├── evidence_match_agent.py    # Agent 2 — match FHIR evidence
│   ├── appeal_draft_agent.py      # Agent 3 — write appeal letter
│   └── orchestrator.py            # Chain all agents
├── mcp_server/                # MCP FHIR tool server
│   ├── main.py                    # FastAPI app + all endpoints
│   ├── fhir_client.py             # FHIR R4 REST client
│   └── sharp_middleware.py        # Prompt Opinion FHIR context handling
├── payer_mock/                # Mock payer API for testing
├── demo_ui/                   # React demo interface
├── scripts/                   # Utility scripts
├── tests/                     # Test suite
├── data/                      # Sample FHIR data + denial letter
├── docs/                      # Documentation
├── requirements.txt
├── railway.toml
└── .env.example
```

---

*Built for the [Agents Assemble Healthcare AI Hackathon](https://agents-assemble.devpost.com/) — Prompt Opinion Marketplace*
