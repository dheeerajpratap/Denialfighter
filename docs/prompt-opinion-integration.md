# Prompt Opinion Integration

DenialFighter publishes its FHIR tools to the Prompt Opinion Marketplace and registers as an A2A agent on the platform. This document covers setup, publishing, and how the integration works technically.

---

## Overview

Prompt Opinion is the platform for this hackathon. It:
- Hosts a marketplace of MCP tools that any agent can call
- Provides an A2A agent runtime where you configure agents that use your tools
- Injects FHIR context (patient ID, FHIR server URL, auth token) into every tool call via SHARP Extension Specs headers

DenialFighter participates in **both tracks**:
- **MCP Superpower** — 5 FHIR reader tools published to the marketplace
- **A2A Agent** — the full pipeline agent configured on the platform

---

## Step 1: Register

1. Go to [app.promptopinion.ai](https://app.promptopinion.ai)
2. Create a free account
3. Get a Gemini API key from [aistudio.google.com](https://aistudio.google.com/app/apikey) — Prompt Opinion requires this for the LLM layer
4. Add the Gemini key in your Prompt Opinion account settings

---

## Step 2: Create a Workspace and Patient

1. In Prompt Opinion dashboard → **New Workspace** → name it `DenialFighter Demo`
2. **Add Patient** → create a test patient record
   - Use the same patient ID as your FHIR server: `132011823`
   - FHIR server URL: `https://hapi.fhir.org/baseR4`

---

## Step 3: Publish Your MCP Server

1. In Prompt Opinion → **Marketplace** → **Add MCP Server**
2. Enter your Railway MCP server URL:
   ```
   https://denialfighter-production.up.railway.app
   ```
3. Prompt Opinion fetches `/.well-known/mcp.json` automatically and discovers all 5 tools:
   - `get_patient_summary`
   - `get_active_medications`
   - `get_conditions`
   - `get_diagnostic_reports`
   - `get_medication_history`
4. Review tool descriptions and input schemas → **Publish**

Your tools are now available to any agent in the Prompt Opinion ecosystem.

---

## Step 4: Configure Your A2A Agent

1. In Prompt Opinion → **Agents** → **New Agent**
2. Configure the agent:
   - **Name:** DenialFighter
   - **Tools:** select all 5 FHIR tools from your published MCP server
   - **System prompt:** describe the prior auth appeal workflow
3. Save and enable the agent

---

## Step 5: Test Within the Platform

1. Go to your patient record in Prompt Opinion
2. Start a conversation with the DenialFighter agent
3. Prompt Opinion injects FHIR context headers on every tool call:
   ```
   x-fhir-server-url: https://hapi.fhir.org/baseR4
   x-patient-id: 132011823
   ```
4. Your MCP tools receive these headers, create a per-request FHIR client, and return patient data

---

## How SHARP Context Works (Technical)

When Prompt Opinion calls one of your MCP tools, it adds three headers to the HTTP request:

| Header | Always Present | Description |
|--------|---------------|-------------|
| `x-fhir-server-url` | Yes | Base URL of the FHIR server |
| `x-fhir-access-token` | No | Bearer token (omitted for public FHIR servers) |
| `x-patient-id` | When patient selected | FHIR Patient resource ID |

Your server handles these in `mcp_server/sharp_middleware.py`:

```python
async def validate_sharp_context(request: Request):
    ctx = {
        "fhir_server_url":   request.headers.get("x-fhir-server-url"),
        "fhir_access_token": request.headers.get("x-fhir-access-token"),
        "patient_id":        request.headers.get("x-patient-id"),
    }
    request.state.po_context = {k: v for k, v in ctx.items() if v}
```

Each tool endpoint then creates a per-request FHIR client using that context:

```python
def _fhir(request: Request) -> FHIRClient:
    ctx = getattr(request.state, "po_context", {})
    return FHIRClient(
        base_url=ctx.get("fhir_server_url"),
        access_token=ctx.get("fhir_access_token"),
    )
```

This means:
- **Standalone / Demo UI:** uses `FHIR_BASE_URL` env var (HAPI public server)
- **From Prompt Opinion:** uses whatever FHIR server the platform specifies for that patient

The same tool works seamlessly in both contexts with zero code changes.

---

## Verifying the Integration

After deploying and publishing, confirm with these checks:

**MCP manifest is reachable:**
```bash
curl https://denialfighter-production.up.railway.app/.well-known/mcp.json
```
Should return JSON with `"schema_version": "v1"` and 5 tools.

**A2A agent card is reachable:**
```bash
curl https://denialfighter-production.up.railway.app/.well-known/agent.json
```
Should return agent card with `"name": "DenialFighter"` and `prior_auth_appeal` skill.

**FHIR tool responds to platform-style call:**
```bash
curl -X POST https://denialfighter-production.up.railway.app/tools/get_conditions \
  -H "Content-Type: application/json" \
  -H "x-fhir-server-url: https://hapi.fhir.org/baseR4" \
  -H "x-patient-id: 132011823" \
  -d "{}"
```
Should return `{"conditions": [...]}`.

---

## Submission Checklist

- [ ] Railway MCP backend deployed and `/health` returns 200
- [ ] `/.well-known/mcp.json` returns all 5 tools
- [ ] `/.well-known/agent.json` returns A2A agent card
- [ ] Prompt Opinion account created
- [ ] MCP server published to Prompt Opinion Marketplace (5 tools visible)
- [ ] A2A agent configured on platform using your MCP tools
- [ ] FHIR context headers working (tested with curl above)
- [ ] Demo UI deployed and reachable
- [ ] 3-minute demo video recorded showing the pipeline working within Prompt Opinion
- [ ] Submitted on Devpost with Railway URL
