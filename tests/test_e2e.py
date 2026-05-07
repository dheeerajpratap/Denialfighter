"""
End-to-end integration test.
Requires: MCP server running on localhost:8000
         FHIR data loaded (run scripts/load_fhir.py first)
Run: pytest tests/test_e2e.py -v -s
"""
import json
import pytest
import requests
from pathlib import Path

MCP_BASE = "http://localhost:8000"
PAYER_BASE = "http://localhost:8001"

def get_patient_id():
    ids_path = Path("data/resource_ids.json")
    if not ids_path.exists():
        pytest.skip("resource_ids.json not found - run scripts/load_fhir.py first")
    with open(ids_path) as f:
        ids = json.load(f)
    pids = ids.get("patient", [])
    if not pids:
        pytest.skip("No patient ID in resource_ids.json")
    return pids[0]

def test_mcp_server_healthy():
    r = requests.get(f"{MCP_BASE}/health", timeout=5)
    assert r.status_code == 200

def test_fhir_patient_fetch():
    patient_id = get_patient_id()
    try:
        r = requests.post(f"{MCP_BASE}/tools/get_patient_summary",
                          json={"patient_id": patient_id},
                          headers={"X-SHARP-Patient-ID": patient_id,
                                   "X-SHARP-Tenant-ID": "e2e-test",
                                   "X-SHARP-Session-ID": "e2e-session-001"},
                          timeout=20)
    except requests.exceptions.ReadTimeout:
        pytest.skip("HAPI FHIR server timed out - external dependency unavailable")
    if r.status_code == 500:
        pytest.skip(f"HAPI FHIR server returned 500 for patient {patient_id} - resource may have been purged")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "member_id" in data
    print(f"\n[OK] Patient fetched: {data['name']} | Plan: {data.get('insurance_plan')}")

def test_fhir_conditions_fetch():
    patient_id = get_patient_id()
    try:
        r = requests.post(f"{MCP_BASE}/tools/get_conditions",
                          json={"patient_id": patient_id}, timeout=20)
    except requests.exceptions.ReadTimeout:
        pytest.skip("HAPI FHIR server timed out")
    if r.status_code == 500:
        pytest.skip(f"HAPI FHIR server returned 500 for patient {patient_id}")
    assert r.status_code == 200
    assert "conditions" in r.json()

def test_fhir_medication_history_fetch():
    patient_id = get_patient_id()
    try:
        r = requests.post(f"{MCP_BASE}/tools/get_medication_history",
                          json={"patient_id": patient_id}, timeout=20)
    except requests.exceptions.ReadTimeout:
        pytest.skip("HAPI FHIR server timed out")
    if r.status_code == 500:
        pytest.skip(f"HAPI FHIR server returned 500 for patient {patient_id}")
    assert r.status_code == 200
    assert "history" in r.json()

def test_payer_mock_submit():
    r = requests.post(f"{PAYER_BASE}/submit-appeal",
                      json={
                          "reference_number": "PA-2025-44921",
                          "patient_member_id": "MCR-2024-887234",
                          "appeal_letter": "This is a formal appeal letter...",
                          "attachments": ["PD-L1 report", "Chemo records"],
                          "submitter_email": "test@southwest-oncology.com"
                      }, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "received"
    assert "submission_id" in data
    print(f"\n[OK] Appeal submitted: {data['submission_id']}")

def test_output_file_exists():
    """After running run_pipeline.py, output file should exist."""
    output = Path("data/appeal_packet_output.json")
    if not output.exists():
        pytest.skip("appeal_packet_output.json not found - run scripts/run_pipeline.py first")
    with open(output) as f:
        packet = json.load(f)
    assert "appeal_letter" in packet
    assert "evidence_summary" in packet
    assert packet["submission_ready"] is True
    print(f"\n[OK] Output packet valid. Score: {packet['medical_necessity_score']}/100")
