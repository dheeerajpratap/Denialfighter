"""
FHIR R4 REST client.
Supports both a static base URL (local dev / Railway) and dynamic
per-request context injected by Prompt Opinion (SHARP Extension Specs).
"""
import os
import requests
from typing import Optional

HAPI_BASE = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
HEADERS = {"Accept": "application/fhir+json"}

# Demo patient fallback — returned when HAPI has no data for this patient ID
_DEMO_PATIENT_ID = "132011823"
_DEMO_DATA = {
    "patient_summary": {
        "patient_id": "132011823",
        "name": "Sarah Chen",
        "dob": "1968-03-14",
        "gender": "female",
        "member_id": "MCR-2024-887234",
        "insurance_plan": "MedAdvantage Premier Plan"
    },
    "active_medications": [
        {
            "drug_name": "Pembrolizumab 200mg IV",
            "drug_code": "J9271",
            "dose": "200mg every 3 weeks",
            "prescriber": "Dr. Emily Rodriguez, MD",
            "start_date": "2024-10-15",
            "status": "active"
        }
    ],
    "conditions": [
        {
            "condition_name": "Non-small cell carcinoma of upper lobe of right lung",
            "icd10_code": "C34.11",
            "onset_date": "2024-06-15",
            "status": "active",
            "severity": "severe"
        },
        {
            "condition_name": "Metastatic malignant neoplasm of lymph nodes",
            "icd10_code": "C77.9",
            "onset_date": "2024-07-01",
            "status": "active",
            "severity": "severe"
        }
    ],
    "diagnostic_reports": [
        {
            "report_name": "PD-L1 Immunohistochemistry",
            "date": "2024-09-30",
            "status": "final",
            "conclusion": "PD-L1 TPS 75% — High expression. Positive for pembrolizumab eligibility.",
            "performing_lab": "Quest Diagnostics"
        },
        {
            "report_name": "CT Chest with Contrast",
            "date": "2024-09-15",
            "status": "final",
            "conclusion": "Stage IIIB NSCLC. 4.2cm right upper lobe mass with mediastinal lymphadenopathy.",
            "performing_lab": "Regional Medical Center Radiology"
        },
        {
            "report_name": "ECOG Performance Status",
            "date": "2024-10-10",
            "status": "final",
            "conclusion": "ECOG performance status 1 — Restricted in strenuous activity but ambulatory.",
            "performing_lab": "Oncology Clinic"
        }
    ],
    "medication_history": [
        {
            "drug_name": "Carboplatin 400mg",
            "start_date": "2024-07-01",
            "end_date": "2024-09-28",
            "reason_stopped": "Disease progression. Grade 2 peripheral neuropathy.",
            "status": "stopped"
        },
        {
            "drug_name": "Paclitaxel 260mg",
            "start_date": "2024-07-01",
            "end_date": "2024-09-28",
            "reason_stopped": "Disease progression on combination chemotherapy.",
            "status": "stopped"
        }
    ]
}

class FHIRClient:
    def __init__(self, base_url: str = None, access_token: str = None):
        self.base_url = base_url or HAPI_BASE
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        if access_token:
            self.session.headers["Authorization"] = f"Bearer {access_token}"

    def get_patient(self, patient_id: str) -> dict:
        r = self.session.get(f"{self.base_url}/Patient/{patient_id}", timeout=15)
        r.raise_for_status()
        return r.json()

    def search(self, resource_type: str, params: dict) -> list:
        r = self.session.get(
            f"{self.base_url}/{resource_type}",
            params=params,
            timeout=15
        )
        r.raise_for_status()
        bundle = r.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    def get_patient_summary(self, patient_id: str) -> dict:
        try:
            p = self.get_patient(patient_id)
            name = p.get("name", [{}])[0]
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            coverage = self.search("Coverage", {"patient": patient_id})
            insurance = {}
            if coverage:
                cov = coverage[0]
                insurance = {
                    "plan": cov.get("class", [{}])[0].get("name", "Unknown Plan"),
                    "member_id": cov.get("subscriberId", "Unknown")
                }
            result = {
                "patient_id": patient_id,
                "name": f"{given} {family}".strip(),
                "dob": p.get("birthDate", ""),
                "gender": p.get("gender", ""),
                "member_id": insurance.get("member_id", "MCR-2024-887234"),
                "insurance_plan": insurance.get("plan", "MedAdvantage Premier Plan")
            }
            if result["name"].strip():
                return result
        except Exception:
            pass
        if patient_id == _DEMO_PATIENT_ID:
            return _DEMO_DATA["patient_summary"]
        raise ValueError(f"Patient {patient_id} not found")

    def get_active_medications(self, patient_id: str) -> list:
        try:
            meds = self.search("MedicationRequest", {"patient": patient_id, "status": "active"})
            result = []
            for m in meds:
                med_ref = m.get("medicationCodeableConcept", {})
                coding = med_ref.get("coding", [{}])[0]
                dosage = m.get("dosageInstruction", [{}])[0]
                result.append({
                    "drug_name": coding.get("display", med_ref.get("text", "Unknown")),
                    "drug_code": coding.get("code", ""),
                    "dose": dosage.get("text", ""),
                    "prescriber": m.get("requester", {}).get("display", ""),
                    "start_date": m.get("authoredOn", ""),
                    "status": m.get("status", "active")
                })
            if result:
                return result
        except Exception:
            pass
        if patient_id == _DEMO_PATIENT_ID:
            return _DEMO_DATA["active_medications"]
        return []

    def get_conditions(self, patient_id: str) -> list:
        try:
            conditions = self.search("Condition", {"patient": patient_id})
            result = []
            for c in conditions:
                coding = c.get("code", {}).get("coding", [{}])[0]
                result.append({
                    "condition_name": coding.get("display", c.get("code", {}).get("text", "")),
                    "icd10_code": coding.get("code", ""),
                    "onset_date": c.get("onsetDateTime", ""),
                    "status": c.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
                    "severity": c.get("severity", {}).get("text", "")
                })
            if result:
                return result
        except Exception:
            pass
        if patient_id == _DEMO_PATIENT_ID:
            return _DEMO_DATA["conditions"]
        return []

    def get_diagnostic_reports(self, patient_id: str) -> list:
        try:
            reports = self.search("DiagnosticReport", {"patient": patient_id})
            result = []
            for r in reports:
                coding = r.get("code", {}).get("coding", [{}])[0]
                result.append({
                    "report_name": coding.get("display", r.get("code", {}).get("text", "")),
                    "date": r.get("effectiveDateTime", ""),
                    "status": r.get("status", ""),
                    "conclusion": r.get("conclusion", ""),
                    "performing_lab": r.get("performer", [{}])[0].get("display", "")
                })
            if result:
                return result
        except Exception:
            pass
        if patient_id == _DEMO_PATIENT_ID:
            return _DEMO_DATA["diagnostic_reports"]
        return []

    def get_medication_history(self, patient_id: str) -> list:
        try:
            meds = self.search("MedicationRequest", {"patient": patient_id})
            result = []
            for m in meds:
                if m.get("status") in ("stopped", "completed", "cancelled"):
                    med_ref = m.get("medicationCodeableConcept", {})
                    coding = med_ref.get("coding", [{}])[0]
                    reason = m.get("statusReason", {}).get("text", "")
                    result.append({
                        "drug_name": coding.get("display", med_ref.get("text", "")),
                        "start_date": m.get("authoredOn", ""),
                        "end_date": m.get("dispenseRequest", {}).get("validityPeriod", {}).get("end", ""),
                        "reason_stopped": reason,
                        "status": m.get("status", "")
                    })
            if result:
                return result
        except Exception:
            pass
        if patient_id == _DEMO_PATIENT_ID:
            return _DEMO_DATA["medication_history"]
        return []
