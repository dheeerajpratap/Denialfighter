# API Reference

Base URL (local): `http://localhost:8000`
Base URL (production): `https://denialfighter-production.up.railway.app`

---

## Discovery Endpoints

### GET /.well-known/mcp.json

Returns the MCP tool manifest. Prompt Opinion reads this URL to register your tools on the marketplace.

**Response:**
```json
{
  "schema_version": "v1",
  "name": "DenialFighter FHIR Reader",
  "description": "Reads patient FHIR chart data to support prior auth appeal generation",
  "version": "1.0.0",
  "tools": [
    {
      "name": "get_patient_summary",
      "description": "Get patient demographics and insurance information from FHIR",
      "input_schema": {
        "type": "object",
        "properties": {
          "patient_id": {"type": "string", "description": "FHIR Patient resource ID"}
        },
        "required": ["patient_id"]
      }
    }
    // ... 4 more tools
  ]
}
```

---

### GET /.well-known/agent.json

Returns the A2A agent card. Enables discovery by any A2A-compatible agent or orchestrator.

**Response:**
```json
{
  "name": "DenialFighter",
  "description": "AI agent that fights insurance prior authorization denials...",
  "url": "https://your-app.railway.app",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "prior_auth_appeal",
      "name": "Prior Authorization Appeal",
      "description": "...",
      "tags": ["healthcare", "prior-auth", "fhir", "appeal", "insurance"]
    }
  ]
}
```

---

## Pipeline API

### POST /run-appeal

Starts the DenialFighter pipeline asynchronously. Returns a `job_id` immediately; poll `/appeal-status/{job_id}` for results.

**Request body:**
```json
{
  "patient_id": "132011823",
  "denial_letter": "MedAdvantage Premier Plan\nDate: April 15, 2025\nReference: PA-2025-44921\n..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `patient_id` | string | Yes | FHIR Patient resource ID |
| `denial_letter` | string | Yes | Full text of the denial letter |

**Response `200 OK`:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

---

### GET /appeal-status/{job_id}

Poll for pipeline progress and results.

**Path parameter:** `job_id` — UUID returned by `/run-appeal`

**Response — in progress:**
```json
{
  "status": "running",
  "steps": [
    {"step": "Fetching FHIR chart via MCP...", "detail": ""},
    {"step": "FHIR chart fetched", "detail": "Patient: Sarah Chen"},
    {"step": "Parsing denial letter (Agent 1)...", "detail": ""}
  ],
  "result": null,
  "error": null
}
```

**Response — complete:**
```json
{
  "status": "done",
  "steps": [
    {"step": "Fetching FHIR chart via MCP...", "detail": ""},
    {"step": "FHIR chart fetched", "detail": "Patient: Sarah Chen"},
    {"step": "Parsing denial letter (Agent 1)...", "detail": ""},
    {"step": "Denial letter parsed", "detail": "Drug: Pembrolizumab 200mg IV | Reasons: MED_NECESSITY, STEP_THERAPY"},
    {"step": "Matching clinical evidence (Agent 2)...", "detail": ""},
    {"step": "Evidence matched", "detail": "Score: 92/100 | Strength: strong"},
    {"step": "Drafting appeal letter (Agent 3)...", "detail": ""},
    {"step": "Appeal letter drafted", "detail": "683 words"},
    {"step": "Preparing submission packet...", "detail": ""},
    {"step": "Done", "detail": "Completed in 87.3s"}
  ],
  "result": {
    "patient_summary": {
      "patient_id": "132011823",
      "name": "Sarah Chen",
      "dob": "1968-03-14",
      "gender": "female",
      "member_id": "MCR-2024-887234",
      "insurance_plan": "MedAdvantage Premier Plan"
    },
    "denial_parsed": {
      "patient_name": "Sarah Chen",
      "member_id": "MCR-2024-887234",
      "denied_drug": "Pembrolizumab 200mg IV",
      "denied_drug_code": "J9271",
      "denial_date": "2025-04-15",
      "denial_reason_codes": ["MED_NECESSITY", "STEP_THERAPY", "MISSING_DOCS"],
      "reference_number": "PA-2025-44921",
      "appeal_deadline": "2025-05-15",
      "urgency": "standard"
    },
    "evidence_summary": {
      "medical_necessity_score": 92,
      "appeal_strength": "strong",
      "appeal_recommended": true,
      "evidence_items": [...],
      "step_therapy_evidence": {
        "satisfied": true,
        "drugs_tried": ["Carboplatin", "Paclitaxel"],
        "failure_reasons": ["Disease progression"]
      }
    },
    "appeal_letter": "Dear Prior Authorization Appeals Department...\n\n[HEADER]\n...",
    "attachments_checklist": [
      "[OK] Appeal letter (this document)",
      "[OK] Original denial letter - Ref: PA-2025-44921",
      "[OK] PD-L1 expression report - Quest Diagnostics, 2024-09-30",
      "[OK] Prior chemotherapy records - Carboplatin/Paclitaxel 2024-07 to 2024-09",
      "[OK] Treating physician statement of medical necessity",
      "[OK] ECOG performance status assessment - Score 1, 2024-10-10"
    ],
    "submission_ready": true,
    "appeal_strength": "strong",
    "medical_necessity_score": 92,
    "processing_time_seconds": 87.3
  },
  "error": null
}
```

**Response — error:**
```json
{
  "status": "error",
  "steps": [...],
  "result": null,
  "error": "GROQ_API_KEY not set"
}
```

**Response `404`:** Job ID not found.

---

## FHIR Tool Endpoints

All tool endpoints follow the same pattern:

- **Method:** `POST`
- **Content-Type:** `application/json`
- **Body:** `{"patient_id": "132011823"}` — can be omitted when Prompt Opinion provides `x-patient-id` header

### SHARP Context Headers (injected by Prompt Opinion)

| Header | Description |
|--------|-------------|
| `x-fhir-server-url` | FHIR server base URL to query |
| `x-fhir-access-token` | Bearer token for FHIR server auth (optional) |
| `x-patient-id` | Patient in scope — overrides `patient_id` in request body |

---

### POST /tools/get_patient_summary

Returns patient demographics and insurance information.

**Request:**
```json
{"patient_id": "132011823"}
```

**Response:**
```json
{
  "patient_id": "132011823",
  "name": "Sarah Chen",
  "dob": "1968-03-14",
  "gender": "female",
  "member_id": "MCR-2024-887234",
  "insurance_plan": "MedAdvantage Premier Plan"
}
```

---

### POST /tools/get_active_medications

Returns currently active medications.

**Response:**
```json
{
  "medications": [
    {
      "drug_name": "Pembrolizumab 200mg IV",
      "drug_code": "J9271",
      "dose": "200mg every 3 weeks",
      "prescriber": "Dr. Emily Rodriguez, MD",
      "start_date": "2024-10-15",
      "status": "active"
    }
  ]
}
```

---

### POST /tools/get_conditions

Returns patient diagnoses with ICD-10 codes.

**Response:**
```json
{
  "conditions": [
    {
      "condition_name": "Non-small cell carcinoma of upper lobe of right lung",
      "icd10_code": "C34.11",
      "onset_date": "2024-06-15",
      "status": "active",
      "severity": "severe"
    }
  ]
}
```

---

### POST /tools/get_diagnostic_reports

Returns lab results, pathology, and imaging reports.

**Response:**
```json
{
  "reports": [
    {
      "report_name": "PD-L1 Immunohistochemistry",
      "date": "2024-09-30",
      "status": "final",
      "conclusion": "PD-L1 TPS 75% — High expression. Positive for pembrolizumab eligibility.",
      "performing_lab": "Quest Diagnostics"
    }
  ]
}
```

---

### POST /tools/get_medication_history

Returns all medications including stopped and completed ones (used to prove step therapy).

**Response:**
```json
{
  "history": [
    {
      "drug_name": "Carboplatin 400mg",
      "start_date": "2024-07-01",
      "end_date": "2024-09-28",
      "reason_stopped": "Disease progression. Grade 2 peripheral neuropathy.",
      "status": "stopped"
    }
  ]
}
```

---

## Health Check

### GET /health

```json
{"status": "ok", "service": "DenialFighter MCP FHIR Reader"}
```

---

## Payer Mock API

Runs on port 8001 (local). Simulates the insurance payer submission endpoint.

### POST /submit-appeal

```json
{
  "reference_number": "PA-2025-44921",
  "appeal_letter": "Dear Appeals Department...",
  "patient_id": "132011823"
}
```

**Response:**
```json
{
  "submission_id": "SUB-2025-99123",
  "status": "received",
  "estimated_decision_days": 30
}
```

### GET /appeal-status/{submission_id}

```json
{
  "submission_id": "SUB-2025-99123",
  "status": "under_review"
}
```

### GET /health

```json
{"status": "ok", "service": "Payer Mock API"}
```
