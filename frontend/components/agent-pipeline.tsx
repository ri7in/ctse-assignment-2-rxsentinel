"use client";

import { motion } from "framer-motion";
import {
  Check,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Pill,
  HeartPulse,
  Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/lib/api";

const AGENTS = [
  { key: "coordinator",          label: "Validate", Icon: ShieldCheck },
  { key: "med_parser",           label: "Parse",    Icon: Pill },
  { key: "interaction_analyzer", label: "Analyze",  Icon: HeartPulse },
  { key: "patient_communicator", label: "Explain",  Icon: Stethoscope },
] as const;

type AgentStatus = "idle" | "running" | "done" | "error";

function deriveAgentState(events: TraceEvent[]): Record<
  string,
  { status: AgentStatus; durationMs: number | null }
> {
  const map: Record<string, { status: AgentStatus; durationMs: number | null }> = {};
  for (const a of AGENTS) map[a.key] = { status: "idle", durationMs: null };
  for (const ev of events) {
    const cur = map[ev.agent];
    if (!cur) continue;
    if (ev.event_type === "enter" && cur.status === "idle") cur.status = "running";
    if (ev.event_type === "exit") {
      cur.status = "done";
      cur.durationMs = ev.duration_ms;
    }
    if (ev.event_type === "error") cur.status = "error";
  }
  return map;
}

/**
 * Horizontal stepper, Linear-style. Each agent is a single row item with an
 * icon, label, and timing. The active step pulses; completed steps show
 * elapsed milliseconds in mono. Connectors between steps fill in as work
 * progresses.
 */
export function AgentPipeline({ events }: { events: TraceEvent[] }) {
  const state = deriveAgentState(events);
  const completed = AGENTS.filter((a) => state[a.key].status === "done").length;
  const total = AGENTS.length;
  const progressPct = (completed / total) * 100;

  return (
    <div className="card p-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-[0.14em] text-foreground-muted">
            Pipeline
          </span>
          <span className="text-[11px] font-mono text-foreground-dim">
            {completed}/{total}
          </span>
        </div>
        <span className="text-[11px] font-mono text-foreground-dim">LangGraph</span>
      </div>

      {/* Continuous progress bar — fills as steps complete */}
      <div className="relative h-1 bg-surface-2 rounded-full overflow-hidden mb-5">
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-[#06B6D4] to-[#0891B2] rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progressPct}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      {/* Steps row */}
      <ol className="grid grid-cols-4 gap-1">
        {AGENTS.map((a, idx) => {
          const s = state[a.key];
          const next = idx < AGENTS.length - 1 ? state[AGENTS[idx + 1].key] : null;
          return (
            <li key={a.key} className="relative">
              <Step status={s.status} label={a.label} Icon={a.Icon} durationMs={s.durationMs} />
              {/* Connector */}
              {idx < AGENTS.length - 1 && (
                <div
                  className={cn(
                    "absolute top-4 right-0 translate-x-1/2 w-2 h-px transition-colors",
                    s.status === "done" || (s.status === "running" && next?.status !== "idle")
                      ? "bg-[#0891B2]"
                      : "bg-border",
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Step({
  status,
  label,
  Icon,
  durationMs,
}: {
  status: AgentStatus;
  label: string;
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  durationMs: number | null;
}) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="relative shrink-0">
        <div
          className={cn(
            "size-8 grid place-items-center rounded-full border transition-colors",
            status === "idle"    && "bg-surface border-border text-foreground-dim",
            status === "running" && "bg-primary-soft border-primary-border text-primary",
            status === "done"    && "bg-severity-low-bg border-severity-low-border text-severity-low",
            status === "error"   && "bg-severity-high-bg border-severity-high-border text-severity-high",
          )}
        >
          {status === "running" ? (
            <Loader2 size={14} className="animate-spin" />
          ) : status === "done" ? (
            <Check size={14} strokeWidth={2.5} />
          ) : status === "error" ? (
            <AlertCircle size={14} strokeWidth={2.5} />
          ) : (
            <Icon size={14} strokeWidth={2} />
          )}
        </div>
        {status === "running" && (
          <span className="absolute inset-0 rounded-full border-2 border-[#0891B2] ring-pulse pointer-events-none" />
        )}
      </div>
      <div className="min-w-0">
        <div
          className={cn(
            "text-xs font-medium truncate",
            status === "idle" ? "text-foreground-dim" : "text-foreground",
          )}
        >
          {label}
        </div>
        {durationMs !== null && (
          <div className="text-[10px] font-mono text-foreground-dim">
            {Math.round(durationMs)}ms
          </div>
        )}
      </div>
    </div>
  );
}
