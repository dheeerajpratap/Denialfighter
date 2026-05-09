# Architecture

## Overview

DenialFighter is built on three pillars:

1. **MCP FHIR Tool Server** — exposes patient chart data as callable tools on the Prompt Opinion Marketplace
2. **A2A Agent Pipeline** — three specialized LLM agents chained sequentially to process a denial end-to-end
3. **Demo UI** — React interface showing the pipeline running in real time

---

## System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        INPUT                                     │
│   Denial Letter (free text)  +  Patient FHIR ID                  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  MCP FHIR READER SERVER                          │
│                  FastAPI on port 8000                            │
│                                                                  │
│  /.well-known/mcp.json     ← Prompt Opinion discovers tools here │
│  /.well-known/agent.json   ← A2A agent card                     │
│                                                                  │
│  SHARP Context Headers (Prompt Opinion injects per-call):        │
│    x-fhir-server-url    → which FHIR server to query             │
│    x-fhir-access-token  → auth token (if required)               │
│    x-patient-id         → patient in scope                       │
│                                                                  │
│  5 Tools:                                                        │
│  • POST /tools/get_patient_summary                               │
│  • POST /tools/get_active_medications                            │
│  • POST /tools/get_conditions                                    │
│  • POST /tools/get_diagnostic_reports                            │
│  • POST /tools/get_medication_history                            │
│                                                                  │
│  Pipeline API (used by Demo UI):                                 │
│  • POST /run-appeal      → start pipeline, returns job_id        │
│  • GET  /appeal-status/{job_id} → poll progress + result         │
└───────────────┬──────────────────────────────────────────────────┘
                │ calls FHIR tools internally
                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FHIR DATA SOURCE                            │
│              HAPI FHIR Server (R4)                               │
│         https://hapi.fhir.org/baseR4  (public test)             │
│                                                                  │
│  Resources used:                                                 │
│  Patient, Coverage, MedicationRequest, Condition,                │
│  DiagnosticReport                                                │
└──────────────────────────────────────────────────────────────────┘
                │ FHIR chart assembled
                ▼
┌──────────────────────────────────────────────────────────────────┐
│              A2A AGENT PIPELINE (Orchestrator)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  AGENT 1 — Denial Intake                               │      │
│  │  Model: Groq LLaMA 3.3-70b-versatile  Temp: 0          │      │
│  │  Input:  Free-text denial letter                        │      │
│  │  Output: Structured JSON                                │      │
│  │    • denied_drug, denied_drug_code                      │      │
│  │    • denial_reason_codes (MED_NECESSITY, STEP_THERAPY,  │      │
│  │      FORMULARY, MISSING_DOCS, OTHER)                    │      │
│  │    • reference_number, appeal_deadline                  │      │
│  │    • missing_documentation list                         │      │
│  │    • urgency (standard / expedited)                     │      │
│  └────────────────────┬───────────────────────────────────┘      │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────┐      │
│  │  AGENT 2 — Evidence Matching                           │      │
│  │  Model: Groq LLaMA 3.3-70b-versatile  Temp: 0          │      │
│  │  Input:  Denial JSON + FHIR chart                       │      │
│  │  Output: Evidence JSON                                  │      │
│  │    • medical_necessity_score (0-100)                    │      │
│  │    • appeal_strength (strong/moderate/weak)             │      │
│  │    • evidence_items (per denial reason, FHIR-sourced)   │      │
│  │    • step_therapy_evidence (drugs tried, failures)      │      │
│  │    • recommended_guidelines (NCCN citations)            │      │
│  │    • appeal_recommended (boolean)                       │      │
│  └────────────────────┬───────────────────────────────────┘      │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────┐      │
│  │  AGENT 3 — Appeal Drafting                             │      │
│  │  Model: Groq LLaMA 3.3-70b-versatile  Temp: 0.1        │      │
│  │  Input:  Denial data + evidence + patient summary       │      │
│  │  Output: Formatted appeal letter                        │      │
│  │    • 8 sections: HEADER, OPENING, CLINICAL BACKGROUND,  │      │
│  │      MEDICAL NECESSITY, STEP THERAPY, GUIDELINES,       │      │
│  │      REQUEST, SIGNATURE BLOCK                           │      │
│  │    • 600-750 words, medical-legal tone                  │      │
│  │    • ATTACHMENTS section included                       │      │
│  └────────────────────┬───────────────────────────────────┘      │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    APPEAL PACKET                                 │
│  • appeal_letter (complete text)                                 │
│  • medical_necessity_score                                       │
│  • appeal_strength                                               │
│  • evidence_summary                                              │
│  • attachments_checklist                                         │
│  • submission_ready (boolean)                                    │
│  • processing_time_seconds                                       │
└─────────────────────┬────────────────────────────────────────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
    ┌─────────────┐       ┌──────────────┐
    │  Demo UI    │       │  Payer Mock  │
    │  React/Vite │       │  POST        │
    │  Real-time  │       │  /submit-    │
    │  polling    │       │  appeal      │
    └─────────────┘       └──────────────┘
```

---

## Component Details

### MCP FHIR Tool Server (`mcp_server/`)

**`main.py`** — FastAPI application
- Serves the MCP manifest and A2A agent card
- Exposes 5 FHIR tool endpoints
- Hosts the async pipeline API (`/run-appeal`, `/appeal-status/{id}`)
- Uses `ThreadPoolExecutor` to run the synchronous agent pipeline without blocking the event loop
- In-memory job store (`_jobs` dict) tracks pipeline state per `job_id`

**`fhir_client.py`** — FHIR R4 REST client
- Wraps `requests.Session` with FHIR accept headers
- Supports dynamic `base_url` and `access_token` (injected per-request by Prompt Opinion)
- Falls back to `FHIR_BASE_URL` env var when no platform context present
- Methods: `get_patient_summary`, `get_active_medications`, `get_conditions`, `get_diagnostic_reports`, `get_medication_history`

**`sharp_middleware.py`** — Prompt Opinion FHIR context handler
- Extracts `x-fhir-server-url`, `x-fhir-access-token`, `x-patient-id` from each request
- Stores context on `request.state.po_context` for downstream use
- `get_patient_id_from_sharp()` returns platform patient ID or falls back to request body

### Agent Pipeline (`agents/`)

Agents are pure functions: `run(input) -> output`. They are stateless and deterministic (temperature 0 except Agent 3).

**`denial_intake_agent.py`**
- System prompt: expert revenue cycle analyst
- Outputs strict JSON schema — never prose
- Handles markdown fence stripping from LLM output
- Temperature 0 for fully deterministic extraction

**`evidence_match_agent.py`**
- System prompt: oncology pharmacist with NCCN guideline knowledge
- Hard rule: only cite evidence explicitly present in FHIR chart (no hallucination)
- Knows NCCN NSCLC v2.2024 — Pembrolizumab Category 1 for PD-L1 TPS ≥ 50%
- Scores evidence 0-100; maps to strong/moderate/weak appeal strength

**`appeal_draft_agent.py`**
- System prompt: board-certified physician and healthcare attorney (73% reversal rate)
- Enforces 8-section structure with exact headers
- Word count constraint: 600-750 words
- Temperature 0.1 — slight variation for natural prose while staying professional

**`orchestrator.py`**
- Chains Agents 1→2→3 sequentially
- Calls all 5 MCP FHIR tools to assemble chart before running agents
- Passes SHARP headers through tool calls for platform compatibility
- Assembles and saves final appeal packet

### Demo UI (`demo_ui/`)

- **Screen 0 — Intake:** displays patient, denied drug, denial letter, appeal deadline
- **Screen 1 — Processing:** real-time pipeline step updates (polls `/appeal-status` every 1.5s), elapsed timer
- **Screen 2 — Results:** appeal letter preview, score gauge, evidence items, attachments checklist, payer submission

API URL configurable via `VITE_API_URL` env var (Vite build-time injection) — defaults to `http://localhost:8000`.

---

## Data Flow: Prompt Opinion vs Standalone

### When called from Prompt Opinion platform:
```
Prompt Opinion → POST /tools/get_conditions
Headers:
  x-fhir-server-url: https://hapi.fhir.org/baseR4
  x-fhir-access-token: (optional)
  x-patient-id: 132011823
Body: {} or {"patient_id": ""}

Server:
  1. validate_sharp_context() extracts headers → request.state.po_context
  2. _fhir(request) creates FHIRClient with platform-provided URL + token
  3. get_patient_id_from_sharp() returns "132011823" from header
  4. FHIRClient queries FHIR server and returns conditions
```

### When called standalone / from Demo UI:
```
Demo UI → POST /tools/get_conditions
Body: {"patient_id": "132011823"}

Server:
  1. validate_sharp_context() finds no platform headers → empty context
  2. _fhir(request) creates FHIRClient with FHIR_BASE_URL env var
  3. get_patient_id_from_sharp() falls back to req.patient_id = "132011823"
  4. FHIRClient queries FHIR server and returns conditions
```

---

## Key Design Decisions

**Why three separate agents instead of one prompt?**
Each agent has a distinct persona and task: a revenue cycle analyst (Agent 1), an oncology pharmacist (Agent 2), and a physician-attorney (Agent 3). Splitting them allows each system prompt to be deep and specialized. A single prompt doing all three jobs would produce shallower output.

**Why Groq instead of OpenAI/Anthropic?**
Groq's LPU inference delivers ~10x faster token generation for LLaMA 3.3-70b versus GPU-hosted models. The pipeline involves three sequential LLM calls — speed compounds. 90-second total time would be 8+ minutes on standard APIs.

**Why HAPI public test server?**
FHIR R4 is the CMS-mandated standard for patient data interoperability. HAPI is the reference implementation. Using the public test server means zero infrastructure for judges to evaluate — real patient data flows through real FHIR APIs.

**Why in-memory job store?**
This is a demo/hackathon build. The async polling pattern (`/run-appeal` → `job_id` → `/appeal-status`) is production-ready architecture; the storage layer is intentionally simple. Production would use Redis or a database.
