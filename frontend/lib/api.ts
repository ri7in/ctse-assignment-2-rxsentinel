/**
 * Thin wrapper around the FastAPI backend.
 *
 * In dev, requests proxy through Next.js rewrites at /api/backend/* to
 * http://localhost:8000/api/*. In prod we'd point NEXT_PUBLIC_BACKEND_URL at
 * the deployed backend.
 */

export type Severity = "high" | "moderate" | "low";

export interface Medication {
  raw_term: string;
  normalized_name: string;
  rxcui: string | null;
  dose: string | null;
  frequency: string | null;
  route: string | null;
  confidence: number;
}

export interface Interaction {
  drug_a: string;
  drug_b: string;
  drug_a_name: string;
  drug_b_name: string;
  severity: Severity;
  mechanism: string;
  clinical_effect: string;
  recommendation: string;
  source: string[];
}

export interface SeveritySummary {
  high: number;
  moderate: number;
  low: number;
}

export interface FinalReport {
  request_id: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  medications: Medication[];
  unparsed_terms: string[];
  interactions: Interaction[];
  severity_summary: SeveritySummary;
  patient_summary: string;
  readability_grade: number;
  limitations: string[];
}

export interface TraceEvent {
  ts: string;
  agent: string;
  event_type: "enter" | "exit" | "tool_call" | "tool_result" | "error" | "llm_token";
  payload: Record<string, unknown>;
  duration_ms: number | null;
  request_id: string;
}

const BASE = "/api/backend";

export async function submitReview(medications: string): Promise<{ request_id: string; started_at: string }> {
  const res = await fetch(`${BASE}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ medications }),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

export async function fetchReport(requestId: string): Promise<FinalReport | null> {
  const res = await fetch(`${BASE}/runs/${requestId}/report`);
  if (res.status === 202) return null;
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Report fetch failed: ${res.status}`);
  return res.json();
}

export function openTraceStream(
  requestId: string,
  onEvent: (e: TraceEvent) => void,
  onError?: (e: Event) => void,
): () => void {
  const url = `${BASE}/runs/${requestId}/events`;
  const es = new EventSource(url);
  const handler = (msg: MessageEvent) => {
    try {
      const parsed = JSON.parse(msg.data) as TraceEvent;
      onEvent(parsed);
    } catch (err) {
      console.warn("Bad SSE event", err);
    }
  };
  ["enter", "exit", "tool_call", "tool_result", "error", "llm_token"].forEach((t) => {
    es.addEventListener(t, handler as EventListener);
  });
  if (onError) es.onerror = onError;
  return () => es.close();
}
