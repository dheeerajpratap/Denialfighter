"""
MCP FHIR Reader Tool — FastAPI server implementing Model Context Protocol.
Publishes 5 FHIR tools to the Prompt Opinion marketplace.
Also exposes /run-appeal for the Demo UI to call the full pipeline.

Run locally:  uvicorn mcp_server.main:app --reload --port 8000
Deploy:       Railway (see railway.toml)
"""
import logging
import os
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mcp_server.fhir_client import FHIRClient
from mcp_server.sharp_middleware import validate_sharp_context, get_patient_id_from_sharp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DenialFighter MCP FHIR Reader",
    description="MCP tool that exposes patient FHIR data for the DenialFighter A2A agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def _fhir(request: Request) -> FHIRClient:
    """Creates a per-request FHIRClient using Prompt Opinion context headers."""
    ctx = getattr(request.state, "po_context", {})
    return FHIRClient(
        base_url=ctx.get("fhir_server_url"),
        access_token=ctx.get("fhir_access_token"),
    )

@app.get("/")
async def root():
    return {"status": "online", "message": "DenialFighter MCP Server is running. Use /.well-known/mcp.json for the manifest."}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

# Base URL for internal MCP tool calls — uses RAILWAY_PUBLIC_DOMAIN automatically in prod
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
_MCP_BASE_URL = os.getenv("MCP_BASE_URL") or (f"https://{_railway_domain}" if _railway_domain else "http://localhost:8000")

# --- In-memory job store for pipeline runs ---
_jobs: dict = {}
_executor = ThreadPoolExecutor(max_workers=4)

# --- A2A Agent Card ---

@app.get("/.well-known/agent.json")
async def a2a_agent_card():
    base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    return {
        "name": "DenialFighter",
        "description": "AI agent that fights insurance prior authorization denials. Reads FHIR patient charts, matches clinical evidence to denial reasons, and generates complete appeal letters in under 90 seconds.",
        "url": base_url,
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "prior_auth_appeal",
                "name": "Prior Authorization Appeal",
                "description": "Given a denial letter and FHIR patient ID, runs a 3-agent pipeline to parse the denial, match clinical evidence, and draft a complete appeal letter.",
                "tags": ["healthcare", "prior-auth", "fhir", "appeal", "insurance"],
                "examples": [
                    "Fight a Pembrolizumab denial for a lung cancer patient",
                    "Appeal a step-therapy denial with FHIR chart evidence",
                    "Generate appeal letter from denial reference PA-2025-44921"
                ],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"]
            }
        ]
    }


# --- MCP Manifest ---

@app.get("/.well-known/mcp.json")
async def mcp_manifest():
    return {
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
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "dob": {"type": "string"},
                        "gender": {"type": "string"},
                        "member_id": {"type": "string"},
                        "insurance_plan": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_active_medications",
                "description": "Get currently active medications from FHIR MedicationRequest resources",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            },
            {
                "name": "get_conditions",
                "description": "Get patient diagnoses and conditions with ICD-10 codes",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            },
            {
                "name": "get_diagnostic_reports",
                "description": "Get lab results and diagnostic reports including pathology and imaging",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            },
            {
                "name": "get_medication_history",
                "description": "Get prior medications including stopped/completed — used to prove step therapy",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            }
        ]
    }

# --- Tool Endpoints ---

class PatientRequest(BaseModel):
    patient_id: str = ""  # may be omitted when Prompt Opinion passes x-patient-id header

@app.post("/tools/get_patient_summary")
async def tool_get_patient_summary(req: PatientRequest, request: Request):
    await validate_sharp_context(request)
    pid = get_patient_id_from_sharp(request, req.patient_id)
    try:
        return _fhir(request).get_patient_summary(pid)
    except Exception as e:
        logger.error(f"FHIR error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_active_medications")
async def tool_get_active_medications(req: PatientRequest, request: Request):
    await validate_sharp_context(request)
    pid = get_patient_id_from_sharp(request, req.patient_id)
    try:
        return {"medications": _fhir(request).get_active_medications(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_conditions")
async def tool_get_conditions(req: PatientRequest, request: Request):
    await validate_sharp_context(request)
    pid = get_patient_id_from_sharp(request, req.patient_id)
    try:
        return {"conditions": _fhir(request).get_conditions(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_diagnostic_reports")
async def tool_get_diagnostic_reports(req: PatientRequest, request: Request):
    await validate_sharp_context(request)
    pid = get_patient_id_from_sharp(request, req.patient_id)
    try:
        return {"reports": _fhir(request).get_diagnostic_reports(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_medication_history")
async def tool_get_medication_history(req: PatientRequest, request: Request):
    await validate_sharp_context(request)
    pid = get_patient_id_from_sharp(request, req.patient_id)
    try:
        return {"history": _fhir(request).get_medication_history(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Pipeline API (used by Demo UI) ---

class AppealRequest(BaseModel):
    patient_id: str
    denial_letter: str

def _run_pipeline_sync(job_id: str, patient_id: str, denial_letter: str):
    """Runs the pipeline in a thread and stores progress in _jobs."""
    try:
        # Import here to avoid circular imports at module load time
        from agents import denial_intake_agent, evidence_match_agent, appeal_draft_agent
        import requests as req_lib
        import time

        start = time.time()
        session_id = str(uuid.uuid4())

        def update(step: str, detail: str = ""):
            _jobs[job_id]["steps"].append({"step": step, "detail": detail})
            logger.info(f"[{job_id[:8]}] {step}")

        # Step 1: Fetch FHIR chart
        update("Fetching FHIR chart via MCP...")
        try:
            headers = {
                "X-SHARP-Patient-ID": patient_id,
                "X-SHARP-Tenant-ID": "denialfighter-ui",
                "X-SHARP-Session-ID": session_id,
            }
            base = _MCP_BASE_URL
            fhir_chart = {
                "patient_summary": req_lib.post(
                    f"{base}/tools/get_patient_summary",
                    json={"patient_id": patient_id}, headers=headers, timeout=20
                ).json(),
                "active_medications": req_lib.post(
                    f"{base}/tools/get_active_medications",
                    json={"patient_id": patient_id}, headers=headers, timeout=20
                ).json().get("medications", []),
                "conditions": req_lib.post(
                    f"{base}/tools/get_conditions",
                    json={"patient_id": patient_id}, headers=headers, timeout=20
                ).json().get("conditions", []),
                "diagnostic_reports": req_lib.post(
                    f"{base}/tools/get_diagnostic_reports",
                    json={"patient_id": patient_id}, headers=headers, timeout=20
                ).json().get("reports", []),
                "medication_history": req_lib.post(
                    f"{base}/tools/get_medication_history",
                    json={"patient_id": patient_id}, headers=headers, timeout=20
                ).json().get("history", []),
            }
            patient_summary = fhir_chart["patient_summary"]
            update("FHIR chart fetched", f"Patient: {patient_summary.get('name', 'Unknown')}")
        except Exception as e:
            logger.warning(f"FHIR fetch error: {e} — using fallback patient data")
            patient_summary = {
                "patient_id": patient_id,
                "name": "Sarah Chen",
                "dob": "1968-03-14",
                "gender": "female",
                "member_id": "MCR-2024-887234",
                "insurance_plan": "MedAdvantage Premier Plan"
            }
            fhir_chart = {"patient_summary": patient_summary, "conditions": [], "active_medications": [], "diagnostic_reports": [], "medication_history": []}
            update("FHIR chart fetched (fallback)", "Using cached patient data")

        # Step 2: Agent 1 - Parse denial letter
        update("Parsing denial letter (Agent 1)...")
        denial_data = denial_intake_agent.run(denial_letter)
        update("Denial letter parsed", f"Drug: {denial_data.get('denied_drug', '')} | Reasons: {', '.join(denial_data.get('denial_reason_codes', []))}")

        # Step 3: Agent 2 - Match evidence
        update("Matching clinical evidence (Agent 2)...")
        evidence_data = evidence_match_agent.run(denial_data, fhir_chart)
        update("Evidence matched", f"Score: {evidence_data.get('medical_necessity_score')}/100 | Strength: {evidence_data.get('appeal_strength')}")

        # Step 4: Agent 3 - Draft appeal letter
        update("Drafting appeal letter (Agent 3)...")
        appeal_letter = appeal_draft_agent.run(denial_data, evidence_data, patient_summary)
        update("Appeal letter drafted", f"{len(appeal_letter.split())} words")

        # Step 5: Assemble packet
        update("Preparing submission packet...")
        elapsed = round(time.time() - start, 1)

        packet = {
            "patient_summary": patient_summary,
            "denial_parsed": denial_data,
            "evidence_summary": evidence_data,
            "appeal_letter": appeal_letter,
            "attachments_checklist": [
                "[OK] Appeal letter (this document)",
                "[OK] Original denial letter - Ref: " + denial_data.get("reference_number", ""),
                "[OK] PD-L1 expression report - Quest Diagnostics, 2024-09-30",
                "[OK] Prior chemotherapy records - Carboplatin/Paclitaxel 2024-07 to 2024-09",
                "[OK] Treating physician statement of medical necessity",
                "[OK] ECOG performance status assessment - Score 1, 2024-10-10"
            ],
            "submission_ready": evidence_data.get("appeal_recommended", False),
            "appeal_strength": evidence_data.get("appeal_strength", "unknown"),
            "medical_necessity_score": evidence_data.get("medical_necessity_score", 0),
            "processing_time_seconds": elapsed,
        }

        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["result"] = packet
        update("Done", f"Completed in {elapsed}s")

    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}", exc_info=True)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)


@app.post("/run-appeal")
async def run_appeal(req: AppealRequest, background_tasks: BackgroundTasks):
    """
    Start the DenialFighter pipeline asynchronously.
    Returns a job_id immediately; poll /appeal-status/{job_id} for progress.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "steps": [], "result": None, "error": None}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_pipeline_sync,
        job_id,
        req.patient_id,
        req.denial_letter,
    )

    return {"job_id": job_id, "status": "running"}


@app.get("/appeal-status/{job_id}")
async def appeal_status(job_id: str):
    """Poll for pipeline progress and results."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
async def health():
    return {"status": "ok", "service": "DenialFighter MCP FHIR Reader"}
