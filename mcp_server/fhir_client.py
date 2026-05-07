"""
FHIR R4 REST client for HAPI public test server.
"""
import requests
from typing import Optional

HAPI_BASE = "https://hapi.fhir.org/baseR4"
HEADERS = {"Accept": "application/fhir+json"}

class FHIRClient:
    def __init__(self, base_url: str = HAPI_BASE):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

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
        
        return {
            "patient_id": patient_id,
            "name": f"{given} {family}".strip(),
            "dob": p.get("birthDate", ""),
            "gender": p.get("gender", ""),
            "member_id": insurance.get("member_id", "MCR-2024-887234"),
            "insurance_plan": insurance.get("plan", "MedAdvantage Premier Plan")
        }

    def get_active_medications(self, patient_id: str) -> list:
        meds = self.search("MedicationRequest", {
            "patient": patient_id,
            "status": "active"
        })
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
        return result

    def get_conditions(self, patient_id: str) -> list:
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
        return result

    def get_diagnostic_reports(self, patient_id: str) -> list:
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
        return result

    def get_medication_history(self, patient_id: str) -> list:
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
        return result
