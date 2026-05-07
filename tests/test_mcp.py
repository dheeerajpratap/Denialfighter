"""Tests for MCP FHIR Reader tool endpoints."""
import pytest
import requests

MCP_BASE = "http://localhost:8000"

def test_health():
    r = requests.get(f"{MCP_BASE}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_manifest():
    r = requests.get(f"{MCP_BASE}/.well-known/mcp.json", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["schema_version"] == "v1"
    assert len(data["tools"]) == 5
    tool_names = [t["name"] for t in data["tools"]]
    assert "get_patient_summary" in tool_names
    assert "get_active_medications" in tool_names
    assert "get_conditions" in tool_names
    assert "get_diagnostic_reports" in tool_names
    assert "get_medication_history" in tool_names

def test_patient_summary_requires_id():
    r = requests.post(f"{MCP_BASE}/tools/get_patient_summary",
                      json={}, timeout=5)
    assert r.status_code == 422  # validation error — missing patient_id

def test_sharp_headers_accepted():
    """Verify SHARP headers are accepted without error (even without real patient)."""
    r = requests.post(
        f"{MCP_BASE}/tools/get_patient_summary",
        json={"patient_id": "test-id-123"},
        headers={
            "X-SHARP-Patient-ID": "test-id-123",
            "X-SHARP-Tenant-ID": "test-tenant",
            "X-SHARP-Session-ID": "session-abc",
        },
        timeout=10
    )
    # Will return 500 (FHIR not found) but NOT 422/400
    assert r.status_code in (200, 500)
