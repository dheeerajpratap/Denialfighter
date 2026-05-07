"""
Agent 1: Denial Intake Agent
Parses a prior auth denial letter and extracts structured data.
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert healthcare revenue cycle analyst specializing in 
prior authorization denials. You extract structured data from denial letters with 
100% accuracy.

Extract ALL information from the denial letter into the exact JSON schema provided.
Rules:
- Never guess or infer data that is not explicitly stated
- Dates must be in ISO format (YYYY-MM-DD)
- missing_documentation must be a list of strings, one per missing item
- denial_reason_code: use "MED_NECESSITY", "STEP_THERAPY", "FORMULARY", "MISSING_DOCS", or "OTHER"
- urgency: "expedited" only if letter explicitly mentions life-threatening or urgent
- Return ONLY the JSON object. No prose, no explanation, no markdown.

Example output structure:
{
  "patient_name": "John Smith",
  "member_id": "MCR-2024-123456",
  "denied_drug": "Pembrolizumab 200mg IV",
  "denied_drug_code": "J9271",
  "denial_date": "2025-04-15",
  "denial_reason_codes": ["MED_NECESSITY", "STEP_THERAPY"],
  "denial_reason_text": "Medical necessity not established. Step therapy not met.",
  "payer_name": "MedAdvantage Premier Plan",
  "reference_number": "PA-2025-44921",
  "appeal_deadline": "2025-05-15",
  "appeals_contact": "appeals@medadvantagepremier.com",
  "missing_documentation": [
    "PD-L1 expression test results",
    "Prior chemotherapy documentation"
  ],
  "step_therapy_required": true,
  "urgency": "standard"
}"""

def run(denial_letter_text: str) -> dict:
    """Parse denial letter and return structured data."""
    print("  [Agent 1] Parsing denial letter...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract all information from this prior authorization denial letter:\n\n{denial_letter_text}"
            }
        ]
    )

    text = response.choices[0].message.content.strip()

    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    result = json.loads(text)
    print(f"  [Agent 1] DONE - Drug: {result.get('denied_drug')}, "
          f"Reasons: {result.get('denial_reason_codes')}")
    return result