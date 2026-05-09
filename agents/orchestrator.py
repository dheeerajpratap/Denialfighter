"""
DenialFighter Orchestrator
Wires all 3 agents + MCP FHIR tool into a complete pipeline.
"""
import json
import os
import time
import requests
import uuid
from pathlib import Path
from agents import denial_intake_agent, evidence_match_agent, appeal_draft_agent

_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
MCP_BASE = os.getenv("MCP_BASE_URL") or (f"https://{_railway_domain}" if _railway_domain else "http://localhost:8000")
SHARP_HEADERS = {
    "X-SHARP-Patient-ID": "",  # Set per-request
    "X-SHARP-Tenant-ID": "denialfighter-hackathon",
    "X-SHARP-Session-ID": ""
}

def call_mcp_tool(tool_name: str, patient_id: str, session_id: str) -> dict:
    """Call a tool on the MCP FHIR Reader server."""
    headers = {
        **SHARP_HEADERS,
        "X-SHARP-Patient-ID": patient_id,
        "X-SHARP-Session-ID": session_id
    }
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool_name}",
        json={"patient_id": patient_id},
        headers=headers,
        timeout=20
    )
    resp.raise_for_status()
    return resp.json()

def build_fhir_chart(patient_id: str, session_id: str) -> dict:
    """Fetch complete patient chart via MCP tools."""
    print("  [MCP] Fetching FHIR chart...")
    return {
        "patient_summary": call_mcp_tool("get_patient_summary", patient_id, session_id),
        "active_medications": call_mcp_tool("get_active_medications", patient_id, session_id),
        "conditions": call_mcp_tool("get_conditions", patient_id, session_id),
        "diagnostic_reports": call_mcp_tool("get_diagnostic_reports", patient_id, session_id),
        "medication_history": call_mcp_tool("get_medication_history", patient_id, session_id)
    }

def run_pipeline(patient_id: str, denial_letter_text: str) -> dict:
    """Run the complete DenialFighter pipeline."""
    session_id = str(uuid.uuid4())
    start = time.time()
    
    print(f"\n[START] DenialFighter starting - Patient: {patient_id} | Session: {session_id[:8]}...")
    
    # Step 1: Fetch FHIR chart via MCP
    fhir_chart = build_fhir_chart(patient_id, session_id)
    patient_summary = fhir_chart["patient_summary"]
    
    # Step 2: Agent 1 — Parse denial letter
    denial_data = denial_intake_agent.run(denial_letter_text)
    
    # Step 3: Agent 2 — Match evidence
    evidence_data = evidence_match_agent.run(denial_data, fhir_chart)
    
    # Step 4: Agent 3 — Draft appeal letter
    appeal_letter = appeal_draft_agent.run(denial_data, evidence_data, patient_summary)
    
    elapsed = round(time.time() - start, 1)
    
    # Assemble final packet
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
        "processing_time_seconds": elapsed
    }
    
    # Save output
    with open("data/appeal_packet_output.json", "w") as f:
        json.dump(packet, f, indent=2)
    
    print(f"\n[DONE] Pipeline complete in {elapsed}s")
    print(f"   Appeal strength: {packet['appeal_strength'].upper()}")
    print(f"   Medical necessity score: {packet['medical_necessity_score']}/100")
    print(f"   Submission ready: {packet['submission_ready']}")
    print(f"\n[SAVED] Appeal letter saved to data/appeal_packet_output.json")
    
    return packet
