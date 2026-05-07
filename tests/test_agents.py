"""Tests for agent parsing logic (unit tests — no API calls)."""
import json
import pytest
from unittest.mock import patch, MagicMock

# ─── Helper: build a mock Groq chat completion response ───

def make_groq_response(text: str):
    """Build a mock Groq-style chat completion response."""
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp

# ─── Agent 1 unit tests ───

def test_denial_intake_parses_json():
    """Agent 1 should return a dict with required keys."""
    mock_result = {
        "patient_name": "Sarah Chen",
        "member_id": "MCR-2024-887234",
        "denied_drug": "Pembrolizumab 200mg IV",
        "denied_drug_code": "J9271",
        "denial_date": "2025-04-15",
        "denial_reason_codes": ["MED_NECESSITY", "STEP_THERAPY", "MISSING_DOCS"],
        "denial_reason_text": "Medical necessity not established. Step therapy not met.",
        "payer_name": "MedAdvantage Premier Plan",
        "reference_number": "PA-2025-44921",
        "appeal_deadline": "2025-05-15",
        "appeals_contact": "appeals@medadvantagepremier.com",
        "missing_documentation": ["PD-L1 expression test results", "ECOG assessment"],
        "step_therapy_required": True,
        "urgency": "standard"
    }

    with patch("agents.denial_intake_agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = make_groq_response(
            json.dumps(mock_result)
        )
        import agents.denial_intake_agent as agent
        result = agent.run("Sample denial letter text")

    assert result["patient_name"] == "Sarah Chen"
    assert "MED_NECESSITY" in result["denial_reason_codes"]
    assert result["reference_number"] == "PA-2025-44921"
    assert result["step_therapy_required"] is True

def test_denial_intake_strips_markdown_fences():
    """Agent 1 should handle ```json ... ``` wrapped responses."""
    mock_result = {"patient_name": "Sarah Chen", "member_id": "MCR-2024-887234",
                   "denied_drug": "Pembrolizumab", "denied_drug_code": "J9271",
                   "denial_date": "2025-04-15", "denial_reason_codes": ["MED_NECESSITY"],
                   "denial_reason_text": "Not established", "payer_name": "MedAdvantage",
                   "reference_number": "PA-2025-44921", "appeal_deadline": "2025-05-15",
                   "appeals_contact": "appeals@test.com", "missing_documentation": [],
                   "step_therapy_required": True, "urgency": "standard"}

    wrapped = f"```json\n{json.dumps(mock_result)}\n```"

    with patch("agents.denial_intake_agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = make_groq_response(wrapped)
        import agents.denial_intake_agent as agent
        result = agent.run("Sample letter")

    assert result["reference_number"] == "PA-2025-44921"

# ─── Agent 2 unit tests ───

def test_evidence_match_returns_score():
    mock_result = {
        "medical_necessity_score": 87,
        "evidence_items": [{"denial_reason_addressed": "STEP_THERAPY", "evidence_type": "prior_treatment",
                            "evidence_description": "Carboplatin + Paclitaxel failed", "fhir_resource_type": "MedicationRequest",
                            "date": "2024-09-28", "strength": "strong"}],
        "step_therapy_evidence": {"satisfied": True, "drugs_tried": ["Carboplatin", "Paclitaxel"],
                                  "failure_reasons": ["Disease progression"]},
        "recommended_guidelines": [],
        "appeal_strength": "strong",
        "appeal_recommended": True,
        "reasoning": "Strong evidence."
    }

    with patch("agents.evidence_match_agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = make_groq_response(
            json.dumps(mock_result)
        )
        import agents.evidence_match_agent as agent
        result = agent.run({"denial_reason_codes": ["STEP_THERAPY"]}, {"conditions": []})

    assert result["medical_necessity_score"] == 87
    assert result["appeal_strength"] == "strong"
    assert result["appeal_recommended"] is True

# ─── Agent 3 unit tests ───

def test_appeal_draft_returns_string():
    mock_letter = "[HEADER]\nApril 27, 2025\n\n[OPENING]\nThis is a formal appeal...\n[REQUEST]\nApprove pembrolizumab."

    with patch("agents.appeal_draft_agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = make_groq_response(mock_letter)
        import agents.appeal_draft_agent as agent
        result = agent.run({}, {}, {"name": "Sarah Chen"})

    assert isinstance(result, str)
    assert "[HEADER]" in result
    assert "[REQUEST]" in result
