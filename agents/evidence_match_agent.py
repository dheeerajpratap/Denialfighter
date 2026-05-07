"""
Agent 2: Evidence Matching Agent
Matches clinical evidence from FHIR chart to each denial reason.
"""
import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a board-certified oncology pharmacist and medical necessity 
reviewer with 15 years of experience winning prior authorization appeals.

You will receive:
1. A structured denial summary (what was denied and why)
2. A patient's complete FHIR chart (medications, conditions, lab results, history)

Your job: Find every piece of clinical evidence in the FHIR chart that supports 
overturning this denial. Be specific. Cite exact FHIR data.

Critical rules:
- NEVER hallucinate evidence. Only cite what is EXPLICITLY in the chart data provided.
- For each denial reason, find at least one piece of evidence that addresses it
- Know NCCN guidelines for oncology: Pembrolizumab monotherapy is guideline-recommended 
  for NSCLC with PD-L1 TPS >= 50% (NCCN NSCLC v2.2024, Category 1 recommendation)
- Step therapy is "satisfied" if prior chemo was tried and documented as failed
- medical_necessity_score: 0-100 based on strength of evidence found
- appeal_strength: "strong" (score >= 70), "moderate" (40-69), "weak" (<40)
- Return ONLY valid JSON. No prose. No markdown.

Output schema:
{
  "medical_necessity_score": 87,
  "evidence_items": [
    {
      "denial_reason_addressed": "STEP_THERAPY",
      "evidence_type": "prior_treatment",
      "evidence_description": "Patient received Carboplatin 400mg + Paclitaxel 175mg/m2 from 2024-07-01 to 2024-09-28. Stopped due to disease progression documented in oncology notes.",
      "fhir_resource_type": "MedicationRequest",
      "date": "2024-09-28",
      "strength": "strong"
    }
  ],
  "step_therapy_evidence": {
    "satisfied": true,
    "drugs_tried": ["Carboplatin", "Paclitaxel"],
    "failure_reasons": ["Disease progression", "Grade 2 peripheral neuropathy"]
  },
  "recommended_guidelines": [
    {
      "guideline_name": "NCCN Clinical Practice Guidelines in Oncology: Non-Small Cell Lung Cancer",
      "organization": "National Comprehensive Cancer Network",
      "version": "v2.2024",
      "recommendation": "Pembrolizumab monotherapy is a Category 1 recommendation for metastatic NSCLC with PD-L1 TPS >= 50% and no EGFR/ALK alterations",
      "supports_appeal": true
    }
  ],
  "appeal_strength": "strong",
  "appeal_recommended": true,
  "reasoning": "Patient has strong clinical justification: documented PD-L1 TPS >= 50% meeting guideline threshold, prior platinum-based chemotherapy failure clearly documented, ECOG PS 1 confirming treatment eligibility."
}"""

def run(denial_data: dict, fhir_chart: dict) -> dict:
    """Match evidence from FHIR chart to denial reasons."""
    print("  [Agent 2] Matching clinical evidence...")
    
    prompt = f"""Denial summary:
{json.dumps(denial_data, indent=2)}

Patient FHIR chart:
{json.dumps(fhir_chart, indent=2)}

Find all evidence supporting an appeal. Return JSON only."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    result = json.loads(text)
    print(f"  [Agent 2] DONE - Score: {result.get('medical_necessity_score')}/100, "
          f"Strength: {result.get('appeal_strength')}")
    return result