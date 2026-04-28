"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, AlertCircle, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/lib/api";

const AGENTS = [
  { key: "coordinator", label: "Coordinator", description: "Validate & route" },
  { key: "med_parser", label: "Med Parser", description: "RxNorm normalize" },
  { key: "interaction_analyzer", label: "Interaction Analyzer", description: "Find interactions" },
  { key: "patient_communicator", label: "Patient Communicator", description: "Plain-English summary" },
] as const;

type AgentStatus = "idle" | "running" | "done" | "error";

function deriveAgentState(events: TraceEvent[]): Record<string, {
  status: AgentStatus;
  durationMs: number | null;
  lastTool?: string;
  toolCount: number;
}> {
  const map: Record<string, {
    status: AgentStatus;
    durationMs: number | null;
    lastTool?: string;
    toolCount: number;
  }> = {};
  for (const a of AGENTS) {
    map[a.key] = { status: "idle", durationMs: null, toolCount: 0 };
  }
  for (const ev of events) {
    const cur = map[ev.agent];
    if (!cur) continue;
    if (ev.event_type === "enter" && cur.status === "idle") cur.status = "running";
    if (ev.event_type === "exit") {
      cur.status = "done";
      cur.durationMs = ev.duration_ms;
    }
    if (ev.event_type === "error") cur.status = "error";
    if (ev.event_type === "tool_call") {
      const tool = (ev.payload?.tool as string | undefined) || "";
      cur.lastTool = tool;
      cur.toolCount += 1;
    }
  }
  return map;
}

export function AgentPipeline({ events }: { events: TraceEvent[] }) {
  const state = deriveAgentState(events);

  return (
    <div className="glass rounded-2xl p-5 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Live Agent Pipeline</h3>
          <p className="text-xs text-foreground-dim mt-0.5">
            Each card streams from the LangGraph trace via Server-Sent Events.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {AGENTS.map((a, idx) => {
          const s = state[a.key];
          const status = s.status;
          return (
            <motion.div
              key={a.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.06 }}
              className={cn(
                "relative rounded-xl border p-4 transition-all duration-300",
                status === "idle" && "border-white/5 bg-white/[0.02]",
                status === "running" && "border-[#06B6D4]/40 bg-[#06B6D4]/5 pulse-ring",
                status === "done" && "border-emerald-500/30 bg-emerald-500/5",
                status === "error" && "border-rose-500/40 bg-rose-500/5",
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-foreground-dim">
                  0{idx + 1}
                </span>
                <StatusIcon status={status} />
              </div>
              <h4 className="text-sm font-semibold text-foreground">
                {a.label}
              </h4>
              <p className="text-xs text-foreground-dim mt-0.5">
                {a.description}
              </p>

              <AnimatePresence>
                {(s.lastTool || s.durationMs) && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-[11px]"
                  >
                    {s.lastTool && (
                      <span className="inline-flex items-center gap-1 text-foreground-muted">
                        <Wrench size={10} /> {s.lastTool}
                      </span>
                    )}
                    {s.durationMs !== null && (
                      <span className="font-mono text-foreground-dim">
                        {Math.round(s.durationMs)}ms
                      </span>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === "running")
    return <Loader2 size={16} className="text-[#06B6D4] animate-spin" />;
  if (status === "done")
    return <Check size={16} className="text-emerald-400" />;
  if (status === "error")
    return <AlertCircle size={16} className="text-rose-400" />;
  return <div className="size-2 rounded-full bg-white/15" />;
}
