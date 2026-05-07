"""
Loads the patient FHIR bundle to HAPI FHIR public test server.
Run: python scripts/load_fhir.py
"""
import json
import requests
import uuid
from pathlib import Path

HAPI_BASE = "https://hapi.fhir.org/baseR4"
BUNDLE_PATH = Path("data/patient_bundle.json")
IDS_PATH = Path("data/resource_ids.json")

def load_bundle():
    print("Loading FHIR bundle to HAPI test server...")
    
    with open(BUNDLE_PATH) as f:
        bundle = json.load(f)
    
    # Post the transaction bundle
    resp = requests.post(
        f"{HAPI_BASE}/",
        json=bundle,
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        timeout=30
    )
    
    if resp.status_code not in (200, 201):
        print(f"ERROR: {resp.status_code} — {resp.text[:500]}")
        return
    
    result_bundle = resp.json()
    resource_ids = {}
    
    for entry in result_bundle.get("entry", []):
        location = entry.get("response", {}).get("location", "")
        if not location:
            continue
        # HAPI returns relative URLs like: Patient/131991027/_history/1
        parts = location.split("/")
        if len(parts) >= 2:
            resource_type = parts[0]
            resource_id = parts[1]
            key = resource_type.lower()
            if key not in resource_ids:
                resource_ids[key] = []
            if resource_id not in resource_ids[key]:
                resource_ids[key].append(resource_id)
    
    with open(IDS_PATH, "w") as f:
        json.dump(resource_ids, f, indent=2)
    
    print("Resource IDs saved:")
    for rtype, ids in resource_ids.items():
        print(f"  {rtype}: {ids}")
    
    print("\nFHIR data loaded successfully")
    return resource_ids

if __name__ == "__main__":
    load_bundle()
