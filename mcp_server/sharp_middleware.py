"""
FHIR context propagation middleware for Prompt Opinion platform (SHARP Extension Specs).

Prompt Opinion injects three headers into every MCP tool call:
  x-fhir-server-url    — base URL of the FHIR server for this request
  x-fhir-access-token  — bearer token (omitted when FHIR server is public)
  x-patient-id         — patient in scope (omitted for system-level calls)
"""
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

# Prompt Opinion FHIR context headers (SHARP Extension Specs)
PO_FHIR_URL_HEADER    = "x-fhir-server-url"
PO_FHIR_TOKEN_HEADER  = "x-fhir-access-token"
PO_PATIENT_ID_HEADER  = "x-patient-id"


async def validate_sharp_context(request: Request):
    """Extracts and stores Prompt Opinion FHIR context from request headers."""
    ctx = {
        "fhir_server_url":   request.headers.get(PO_FHIR_URL_HEADER),
        "fhir_access_token": request.headers.get(PO_FHIR_TOKEN_HEADER),
        "patient_id":        request.headers.get(PO_PATIENT_ID_HEADER),
    }
    ctx = {k: v for k, v in ctx.items() if v}  # drop None values

    if ctx:
        safe = {k: v for k, v in ctx.items() if k != "fhir_access_token"}
        logger.info(f"Prompt Opinion FHIR context: {safe}")

    request.state.po_context = ctx
    return ctx


def get_patient_id_from_sharp(request: Request, fallback_patient_id: str = None) -> str:
    """Returns patient ID from Prompt Opinion context header, or falls back to request param."""
    ctx = getattr(request.state, "po_context", {})
    return ctx.get("patient_id") or fallback_patient_id
