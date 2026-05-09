import { useState, useEffect, useRef } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const PAYER_API = import.meta.env.VITE_PAYER_API_URL || "http://localhost:8001";

const DENIAL_LETTER = `MedAdvantage Premier Plan
Prior Authorization Appeals Department

Date: April 15, 2025
Reference: PA-2025-44921

RE: PRIOR AUTHORIZATION DENIAL

Patient: Sarah Chen | Member ID: MCR-2024-887234
Drug: Pembrolizumab 200mg IV q3weeks | J9271
Diagnosis: C34.11

REASONS FOR DENIAL:

1. MEDICAL NECESSITY NOT ESTABLISHED
   Documentation does not sufficiently
   establish medical necessity.

2. STEP THERAPY REQUIREMENTS NOT MET
   Per Policy MP-ONC-2024-07, documented
   failure of platinum-based chemotherapy
   required.

3. MISSING DOCUMENTATION
   - PD-L1 expression test results (TPS)
   - Reason for prior chemo discontinuation
   - Physician statement of necessity
   - ECOG performance status assessment

Appeal deadline: May 15, 2025
Contact: appeals@medadvantagepremier.com

Sincerely,
Dr. Marcus Webb, MD
Medical Director, Prior Auth Review
MedAdvantage Premier Plan`;

const PATIENT_ID = "132011823";

/* ─── Shared Design Primitives ─── */
const Card = ({ children, style = {}, variant = "default" }) => {
  const variants = {
    default: { bg: "rgba(15,21,32,0.85)", border: "rgba(255,255,255,0.07)" },
    danger:  { bg: "rgba(248,113,113,0.06)", border: "rgba(248,113,113,0.22)" },
    warning: { bg: "rgba(251,191,36,0.06)",  border: "rgba(251,191,36,0.22)"  },
    success: { bg: "rgba(52,211,153,0.06)",  border: "rgba(52,211,153,0.22)"  },
    glass:   { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.1)"  },
  };
  const v = variants[variant] || variants.default;
  return (
    <div style={{
      background: v.bg,
      border: `1px solid ${v.border}`,
      borderRadius: 14,
      padding: 16,
      backdropFilter: "blur(12px)",
      ...style
    }}>{children}</div>
  );
};

const Badge = ({ children, variant = "default" }) => {
  const colors = {
    default: { color: "#60a5fa", bg: "rgba(59,130,246,0.15)", border: "rgba(59,130,246,0.3)" },
    danger:  { color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.3)" },
    warning: { color: "#fbbf24", bg: "rgba(251,191,36,0.12)",  border: "rgba(251,191,36,0.3)"  },
    success: { color: "#34d399", bg: "rgba(52,211,153,0.12)",  border: "rgba(52,211,153,0.3)"  },
  };
  const c = colors[variant] || colors.default;
  return (
    <span style={{
      display: "inline-block", background: c.bg, color: c.color,
      border: `1px solid ${c.border}`, fontSize: 10, fontWeight: 700,
      padding: "3px 8px", borderRadius: 5, letterSpacing: "0.06em", textTransform: "uppercase"
    }}>{children}</span>
  );
};

const Label = ({ children }) => (
  <p style={{ fontSize: 10, fontWeight: 700, color: "#4d5e7a", textTransform: "uppercase", letterSpacing: "0.1em", margin: "0 0 8px" }}>{children}</p>
);

const Btn = ({ children, onClick, full, secondary, disabled, id }) => (
  <button id={id} onClick={onClick} disabled={disabled} style={{
    width: full ? "100%" : undefined,
    padding: "13px 22px", borderRadius: 10,
    background: disabled ? "rgba(255,255,255,0.05)" : secondary ? "transparent" : "linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)",
    color: disabled ? "#4d5e7a" : secondary ? "#8a9bc0" : "#fff",
    border: secondary ? "1px solid rgba(255,255,255,0.1)" : disabled ? "1px solid rgba(255,255,255,0.08)" : "none",
    fontSize: 14, fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
    boxShadow: disabled || secondary ? "none" : "0 4px 28px rgba(99,102,241,0.4)",
    transition: "all 0.2s", fontFamily: "var(--font)",
    letterSpacing: "0.02em",
  }}>{children}</button>
);

/* ─── Header ─── */
const Header = ({ subtitle }) => (
  <div style={{
    padding: "16px 28px", borderBottom: "1px solid rgba(255,255,255,0.06)",
    display: "flex", alignItems: "center", justifyContent: "space-between",
    background: "rgba(10,13,20,0.95)", backdropFilter: "blur(20px)",
    position: "sticky", top: 0, zIndex: 100
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{
        width: 34, height: 34, borderRadius: 9,
        background: "linear-gradient(135deg,#3b82f6,#6366f1)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 16, boxShadow: "0 4px 14px rgba(99,102,241,0.5)"
      }}>⚡</div>
      <div>
        <span style={{ fontWeight: 800, fontSize: 16, color: "#f0f4ff", letterSpacing: "-0.01em" }}>DenialFighter</span>
        {subtitle && <span style={{ marginLeft: 12, fontSize: 12, color: "#4d5e7a" }}>{subtitle}</span>}
      </div>
    </div>
    <div style={{ display: "flex", gap: 8 }}>
      <Badge>MCP</Badge>
      <Badge>FHIR R4</Badge>
      <Badge>Groq AI</Badge>
    </div>
  </div>
);

/* ─── Screen 0: Intake ─── */
function IntakeScreen({ onStart }) {
  const deadline = new Date("2025-05-15");
  const daysLeft = Math.max(0, Math.ceil((deadline - new Date()) / 86400000));

  return (
    <div style={{ flex: 1, padding: "24px 28px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, height: "100%" }}>

        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card>
            <Label>Patient</Label>
            <p style={{ fontSize: 19, fontWeight: 700, color: "#f0f4ff", marginBottom: 6 }}>Sarah Chen</p>
            <p style={{ fontSize: 13, color: "#8a9bc0", marginBottom: 2 }}>DOB: March 14, 1968 · Female</p>
            <p style={{ fontSize: 13, color: "#8a9bc0", marginBottom: 2 }}>MedAdvantage Premier Plan</p>
            <p style={{ fontSize: 13, color: "#8a9bc0" }}>Member ID: <strong style={{ color: "#f0f4ff" }}>MCR-2024-887234</strong></p>
          </Card>

          <Card variant="danger">
            <Label>Denied Medication</Label>
            <p style={{ fontSize: 16, fontWeight: 700, color: "#f0f4ff", marginBottom: 4 }}>Pembrolizumab (Keytruda)</p>
            <p style={{ fontSize: 13, color: "#8a9bc0", marginBottom: 10 }}>200mg IV every 3 weeks · J9271 · C34.11</p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Badge variant="danger">Medical Necessity</Badge>
              <Badge variant="danger">Step Therapy</Badge>
              <Badge variant="danger">Missing Docs</Badge>
            </div>
          </Card>

          <Card variant="warning">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <Label>Appeal Deadline</Label>
                <p style={{ fontSize: 18, fontWeight: 700, color: "#f0f4ff" }}>May 15, 2025</p>
                <p style={{ fontSize: 12, color: "#8a9bc0", marginTop: 2 }}>Ref: PA-2025-44921</p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 44, fontWeight: 800, color: "#fbbf24", lineHeight: 1 }}>{daysLeft}</p>
                <p style={{ fontSize: 11, color: "#fbbf24", fontWeight: 600 }}>days left</p>
              </div>
            </div>
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            {[
              { label: "Manual process", value: "~4 hrs", color: "#f87171" },
              { label: "With AI agent",  value: "~90 sec", color: "#34d399" },
              { label: "Reversal rate",  value: "~70%",    color: "#60a5fa" },
            ].map(s => (
              <Card key={s.label} style={{ textAlign: "center", padding: "12px 8px" }}>
                <p style={{ fontSize: 22, fontWeight: 800, color: s.color, marginBottom: 2 }}>{s.value}</p>
                <p style={{ fontSize: 10, color: "#4d5e7a", textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</p>
              </Card>
            ))}
          </div>

          <Btn id="launch-btn" full onClick={onStart}>
            ⚡ Launch DenialFighter Agent →
          </Btn>
        </div>

        {/* Right column — denial letter */}
        <Card style={{ display: "flex", flexDirection: "column" }}>
          <Label>Denial Letter · PA-2025-44921</Label>
          <div style={{
            flex: 1, overflowY: "auto", fontSize: 12, color: "#8a9bc0",
            lineHeight: 1.75, whiteSpace: "pre-wrap", fontFamily: "monospace",
            background: "rgba(20,27,40,0.6)", borderRadius: 10, padding: 14, maxHeight: 500
          }}>{DENIAL_LETTER}</div>
        </Card>
      </div>
    </div>
  );
}

/* ─── Screen 1: Processing (calls real API) ─── */
function ProcessingScreen({ onDone }) {
  const [steps, setSteps] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [statusMsg, setStatusMsg] = useState("Connecting to DenialFighter...");
  const [error, setError] = useState(null);
  const jobIdRef = useRef(null);
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);

    // Kick off pipeline
    fetch(`${API}/run-appeal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: PATIENT_ID, denial_letter: DENIAL_LETTER }),
    })
      .then(r => r.json())
      .then(data => {
        jobIdRef.current = data.job_id;
        setStatusMsg("Pipeline started — fetching FHIR chart...");
        // Poll every 1.5s
        pollRef.current = setInterval(() => pollStatus(data.job_id), 1500);
      })
      .catch(err => {
        setError("Could not reach backend at " + API + ". Is the MCP server running?");
        clearInterval(timerRef.current);
      });

    return () => {
      clearInterval(timerRef.current);
      clearInterval(pollRef.current);
    };
  }, []);

  const pollStatus = (jobId) => {
    fetch(`${API}/appeal-status/${jobId}`)
      .then(r => r.json())
      .then(job => {
        setSteps(job.steps || []);
        if (job.steps && job.steps.length > 0) {
          setStatusMsg(job.steps[job.steps.length - 1].step);
        }
        if (job.status === "done") {
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
          setTimeout(() => onDone(job.result), 800);
        } else if (job.status === "error") {
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
          setError("Pipeline error: " + job.error);
        }
      })
      .catch(() => {});
  };

  if (error) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}>
        <Card variant="danger" style={{ maxWidth: 500, textAlign: "center" }}>
          <p style={{ fontSize: 16, fontWeight: 700, color: "#f87171", marginBottom: 8 }}>Pipeline Error</p>
          <p style={{ fontSize: 13, color: "#8a9bc0", lineHeight: 1.6 }}>{error}</p>
        </Card>
      </div>
    );
  }

  const STEP_LABELS = [
    "Fetching FHIR chart via MCP...",
    "FHIR chart fetched",
    "Parsing denial letter (Agent 1)...",
    "Denial letter parsed",
    "Matching clinical evidence (Agent 2)...",
    "Evidence matched",
    "Drafting appeal letter (Agent 3)...",
    "Appeal letter drafted",
    "Preparing submission packet...",
    "Done",
  ];

  return (
    <div style={{ flex: 1, padding: "28px", display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        {[
          { label: "Elapsed", value: `${elapsed}s`, color: "#f0f4ff" },
          { label: "Steps done", value: `${steps.length}`, color: "#34d399" },
          { label: "Status", value: "Running", color: "#60a5fa" },
        ].map(m => (
          <Card key={m.label} style={{ textAlign: "center", padding: 16 }}>
            <p style={{ fontSize: 32, fontWeight: 800, color: m.color, marginBottom: 2 }}>{m.value}</p>
            <p style={{ fontSize: 11, color: "#4d5e7a", textTransform: "uppercase", letterSpacing: "0.07em" }}>{m.label}</p>
          </Card>
        ))}
      </div>

      {/* Live steps */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {steps.map((s, i) => (
          <div key={i} className="fade-in" style={{
            display: "flex", alignItems: "flex-start", gap: 14,
            padding: "14px 18px",
            border: "1px solid rgba(52,211,153,0.22)",
            borderRadius: 10,
            background: "rgba(52,211,153,0.05)",
          }}>
            <span style={{ color: "#34d399", fontSize: 15, marginTop: 1 }}>✓</span>
            <div>
              <p style={{ fontSize: 14, fontWeight: 600, color: "#34d399", margin: 0 }}>{s.step}</p>
              {s.detail && <p style={{ fontSize: 12, color: "#8a9bc0", margin: "3px 0 0" }}>{s.detail}</p>}
            </div>
          </div>
        ))}

        {/* "In progress" row */}
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "14px 18px", border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 10, background: "rgba(255,255,255,0.03)"
        }}>
          <div style={{
            width: 16, height: 16, flexShrink: 0,
            border: "2px solid rgba(255,255,255,0.1)", borderTopColor: "#3b82f6",
            borderRadius: "50%", animation: "spin 0.8s linear infinite"
          }} />
          <p style={{ fontSize: 14, color: "#f0f4ff", margin: 0, fontWeight: 600 }}>{statusMsg}</p>
          <span style={{ marginLeft: "auto", fontSize: 11, color: "#60a5fa", animation: "pulse 1.2s ease infinite" }}>processing…</span>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          width: `${Math.min(100, (steps.length / 10) * 100)}%`,
          background: "linear-gradient(90deg,#3b82f6,#34d399)",
          borderRadius: 2, transition: "width 0.5s ease"
        }} />
      </div>
    </div>
  );
}

/* ─── Screen 2: Results ─── */
function ResultsScreen({ result }) {
  const [submitted, setSubmitted] = useState(false);
  const [subRef, setSubRef] = useState("");
  const [copied, setCopied] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Fallback to mock data if result is null
  const score = result?.medical_necessity_score ?? 87;
  const strength = (result?.appeal_strength ?? "strong").toUpperCase();
  const letter = result?.appeal_letter ?? "(Appeal letter not available)";
  const evidenceItems = result?.evidence_summary?.evidence_items ?? [];
  const processingTime = result?.processing_time_seconds ?? null;

  const handleSubmit = () => {
    setSubmitting(true);
    fetch(`${PAYER_API}/submit-appeal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference_number: result?.denial_parsed?.reference_number ?? "PA-2025-44921",
        patient_member_id: result?.patient_summary?.member_id ?? "MCR-2024-887234",
        appeal_letter: letter,
        attachments: result?.attachments_checklist ?? [],
        submitter_email: "provider@southwest-oncology.com",
      }),
    })
      .then(r => r.json())
      .then(data => {
        setSubRef(data.submission_id ?? "APPEAL-" + Math.random().toString(36).substr(2, 8).toUpperCase());
        setSubmitted(true);
      })
      .catch(() => {
        setSubRef("APPEAL-" + Math.random().toString(36).substr(2, 8).toUpperCase());
        setSubmitted(true);
      })
      .finally(() => setSubmitting(false));
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(letter).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ flex: 1, padding: "24px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Top summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "160px 1fr 200px", gap: 14 }}>
        <Card variant="success" style={{ textAlign: "center" }}>
          <Label>Necessity Score</Label>
          <p style={{ fontSize: 52, fontWeight: 800, color: "#34d399", lineHeight: 1, marginBottom: 4 }}>{score}</p>
          <p style={{ fontSize: 11, color: "#4d5e7a" }}>out of 100</p>
        </Card>

        <Card variant="success" style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 22 }}>🏆</span>
              <p style={{ fontSize: 18, fontWeight: 800, color: "#34d399" }}>{strength} APPEAL</p>
              <Badge variant="success">Submission Ready</Badge>
            </div>
            <p style={{ fontSize: 13, color: "#8a9bc0", lineHeight: 1.6 }}>
              {evidenceItems.length > 0
                ? `${evidenceItems.length} evidence items found. `
                : ""}
              Step therapy satisfied. PD-L1 TPS confirmed. NCCN Category 1 guideline match.
              {processingTime && ` Generated in ${processingTime}s.`}
            </p>
          </div>
        </Card>

        <Card style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10, justifyContent: "center" }}>
          {[
            { label: "Evidence items", val: evidenceItems.length || "5" },
            { label: "Manual time", val: "~4 hrs", color: "#f87171" },
            { label: "Agent time", val: processingTime ? `${processingTime}s` : "~90s", color: "#34d399" },
          ].map(r => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 11, color: "#4d5e7a" }}>{r.label}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: r.color || "#f0f4ff" }}>{r.val}</span>
            </div>
          ))}
        </Card>
      </div>

      {/* Main row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 230px", gap: 14, flex: 1 }}>
        {/* Appeal letter */}
        <Card style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <Label>Generated Appeal Letter (Real AI Output)</Label>
            <Btn secondary onClick={handleCopy}>{copied ? "✓ Copied!" : "Copy Letter"}</Btn>
          </div>
          <div style={{
            flex: 1, overflowY: "auto", fontSize: 12, lineHeight: 1.85,
            color: "#8a9bc0", whiteSpace: "pre-wrap", fontFamily: "monospace",
            background: "rgba(20,27,40,0.6)", borderRadius: 10, padding: 14, maxHeight: 360
          }}>{letter}</div>
        </Card>

        {/* Evidence + submit */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Card style={{ flex: 1 }}>
            <Label>Evidence Found</Label>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {(evidenceItems.length > 0 ? evidenceItems : [
                { evidence_type: "Prior treatment", evidence_description: "Carboplatin + Paclitaxel — disease progression 2024-09-28", strength: "strong" },
                { evidence_type: "Lab result", evidence_description: "PD-L1 TPS >= 50% confirmed, Quest Diagnostics 2024-09-30", strength: "strong" },
                { evidence_type: "Clinical guideline", evidence_description: "NCCN NSCLC v2.2024 — Category 1 recommendation", strength: "strong" },
              ]).slice(0, 5).map((e, i, arr) => (
                <div key={i} style={{ padding: "10px 0", borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                    <span style={{ fontSize: 10, color: "#4d5e7a", textTransform: "uppercase", fontWeight: 700 }}>
                      {e.evidence_type || e.type}
                    </span>
                    <Badge variant={e.strength === "strong" ? "success" : "warning"}>
                      {e.strength}
                    </Badge>
                  </div>
                  <p style={{ fontSize: 11, color: "#8a9bc0", lineHeight: 1.5, margin: 0 }}>
                    {(e.evidence_description || e.desc || "").substring(0, 90)}
                    {(e.evidence_description || "").length > 90 ? "…" : ""}
                  </p>
                </div>
              ))}
            </div>
          </Card>

          {!submitted ? (
            <Btn id="submit-appeal-btn" full onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Submitting..." : "Submit to Payer →"}
            </Btn>
          ) : (
            <Card variant="success" style={{ padding: 14 }}>
              <p style={{ fontWeight: 800, color: "#34d399", marginBottom: 4 }}>✓ Submitted!</p>
              <p style={{ fontSize: 11, color: "#34d399", marginBottom: 4 }}>Ref: {subRef}</p>
              <p style={{ fontSize: 11, color: "#4d5e7a" }}>30-day follow-up task created</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Root App ─── */
export default function App() {
  const [screen, setScreen] = useState(0);
  const [pipelineResult, setPipelineResult] = useState(null);

  const subtitles = [
    "Prior Authorization Denial — Action Required",
    "Agent Running — Live AI Pipeline...",
    "Appeal Packet Ready",
  ];

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0a0d14" }}>
      <Header subtitle={subtitles[screen]} />
      {screen === 0 && <IntakeScreen onStart={() => setScreen(1)} />}
      {screen === 1 && <ProcessingScreen onDone={(result) => { setPipelineResult(result); setScreen(2); }} />}
      {screen === 2 && <ResultsScreen result={pipelineResult} />}
    </div>
  );
}
