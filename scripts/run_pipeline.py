"""
Runs the complete DenialFighter pipeline end to end.
Requires: MCP server running on localhost:8000
Run: python scripts/run_pipeline.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import run_pipeline

def main():
    # Load patient ID from Phase 1
    ids_path = Path("data/resource_ids.json")
    if not ids_path.exists():
        print("[ERROR] No resource_ids.json found. Run scripts/load_fhir.py first.")
        return
    
    with open(ids_path) as f:
        ids = json.load(f)
    
    patient_ids = ids.get("patient", [])
    if not patient_ids:
        print("[ERROR] No patient ID found. Run scripts/load_fhir.py first.")
        return
    
    patient_id = patient_ids[0]
    denial_letter = Path("data/denial_letter.txt").read_text()
    
    print(f"Patient ID: {patient_id}")
    print(f"Denial letter: {len(denial_letter)} characters")
    
    packet = run_pipeline(patient_id, denial_letter)
    
    print("\n" + "="*60)
    print("APPEAL LETTER PREVIEW")
    print("="*60)
    print(packet["appeal_letter"][:1500])
    print("\n[...letter continues in data/appeal_packet_output.json]")
    
    print("\n" + "="*60)
    print("ATTACHMENTS CHECKLIST")
    print("="*60)
    for item in packet["attachments_checklist"]:
        print(f"  {item}")

if __name__ == "__main__":
    main()
