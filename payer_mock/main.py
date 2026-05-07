"""
Mock Payer Submission API
Simulates submitting an appeal to a payer's API endpoint.

Run: uvicorn payer_mock.main:app --port 8001
"""
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="MedAdvantage Premier — Appeal Submission API (Mock)")

class AppealSubmission(BaseModel):
    reference_number: str
    patient_member_id: str
    appeal_letter: str
    attachments: List[str]
    submitter_email: Optional[str] = "provider@southwest-oncology.com"

submissions = {}

@app.post("/submit-appeal")
async def submit_appeal(submission: AppealSubmission):
    submission_id = f"APPEAL-{str(uuid.uuid4())[:8].upper()}"
    timestamp = datetime.utcnow().isoformat()
    
    record = {
        "submission_id": submission_id,
        "original_reference": submission.reference_number,
        "patient_member_id": submission.patient_member_id,
        "status": "received",
        "received_at": timestamp,
        "estimated_response_date": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "estimated_response_days": 30,
        "confirmation_email_sent_to": submission.submitter_email,
        "message": (
            "Appeal received and assigned to clinical review team. "
            "You will receive a decision within 30 days. "
            "Expedited review available if clinically urgent."
        )
    }
    
    submissions[submission_id] = record
    print(f"[MOCK PAYER] Appeal received: {submission_id} for patient {submission.patient_member_id}")
    return record

@app.get("/appeal-status/{submission_id}")
async def get_status(submission_id: str):
    if submission_id not in submissions:
        return {"error": "Submission not found"}
    return submissions[submission_id]

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedAdvantage Mock Appeals API"}
