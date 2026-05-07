"""
Verifies all Phase 1 setup is correct.
Run: python scripts/verify_setup.py
"""
import json
import requests
from pathlib import Path

HAPI_BASE = "https://hapi.fhir.org/baseR4"

def verify():
    errors = []
    
    # Check files exist
    for f in ["data/patient_bundle.json", "data/denial_letter.txt", "data/resource_ids.json"]:
        if not Path(f).exists():
            errors.append(f"Missing file: {f}")
    
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return False
    
    # Check FHIR resources accessible
    with open("data/resource_ids.json") as f:
        ids = json.load(f)
    
    patient_ids = ids.get("patient", [])
    if not patient_ids:
        errors.append("No patient ID in resource_ids.json")
    else:
        pid = patient_ids[0]
        resp = requests.get(f"{HAPI_BASE}/Patient/{pid}", timeout=10)
        if resp.status_code != 200:
            errors.append(f"Patient {pid} not accessible on HAPI: {resp.status_code}")
        else:
            print(f"[OK] Patient accessible: {pid}")
    
    # Check denial letter has content
    letter = Path("data/denial_letter.txt").read_text()
    if "PA-2025-44921" not in letter:
        errors.append("Denial letter missing reference number")
    else:
        print("[OK] Denial letter valid")
    
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return False
    
    print("\nPHASE 1 COMPLETE -- Ready to build MCP server")
    return True

if __name__ == "__main__":
    verify()
