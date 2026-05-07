"""
Agent 3: Appeal Draft Agent
Writes the complete, formatted prior auth appeal letter.
"""
import json
import os
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a board-certified physician and healthcare attorney who writes 
winning prior authorization appeal letters professionally. You have a 73% reversal rate.

Write the appeal letter following these exact rules:
1. Professional medical-legal tone throughout — never casual
2. Every clinical claim MUST reference specific evidence from the input data
3. No vague statements like "studies show" — only specific citations with dates
4. Structure the letter in exactly these 8 sections with these exact headers:
   - [HEADER] (date, payer address, RE: line)
   - [OPENING] (formal appeal statement, legal basis, what is being appealed)
   - [CLINICAL BACKGROUND] (patient history, diagnosis, why this specific drug)
   - [MEDICAL NECESSITY ARGUMENT] (address each denial reason with cited evidence)
   - [STEP THERAPY COMPLIANCE] (prove prior treatments tried and failed)
   - [CLINICAL GUIDELINE SUPPORT] (cite specific guideline name, version, recommendation)
   - [REQUEST] (specific, unambiguous ask for approval)
   - [SIGNATURE BLOCK] (provider name, NPI, contact)
5. Total length: 600-750 words. Never exceed 750 words.
6. End the letter with an ATTACHMENTS section listing every document being submitted
7. Return ONLY the letter text. No JSON, no explanation."""

def run(denial_data: dict, evidence_data: dict, patient_summary: dict) -> str:
    """Draft the complete appeal letter."""
    print("  [Agent 3] Drafting appeal letter...")
    
    today = datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""Write a complete prior authorization appeal letter using this data:

TODAY'S DATE: {today}

PATIENT:
{json.dumps(patient_summary, indent=2)}

DENIAL INFORMATION:
{json.dumps(denial_data, indent=2)}

CLINICAL EVIDENCE TO USE:
{json.dumps(evidence_data, indent=2)}

Write the complete, formatted appeal letter now. 600-750 words. All 8 sections. 
Letter text only."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1500,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    
    letter = response.choices[0].message.content.strip()
    word_count = len(letter.split())
    print(f"  [Agent 3] DONE - Letter drafted - {word_count} words")
    return letter