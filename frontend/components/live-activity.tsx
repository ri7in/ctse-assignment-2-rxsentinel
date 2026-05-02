"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Activity,
  Sparkles,
  Stethoscope,
  ShieldCheck,
  Wand2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import type { TraceEvent } from "@/lib/api";

interface LiveActivityProps {
  events: TraceEvent[];
  done: boolean;
}

interface Frame {
  key: string;
  text: string;
  Icon: React.ComponentType<{ size?: number; className?: string; strokeWidth?: number }>;
  tone: "info" | "warn" | "success";
}

/**
 * One-line streaming status of what the agents are doing right now.
 * Frames update on every meaningful trace event; tiny dot animation +
 * caret give continuous "alive" feedback.
 */
export function LiveActivity({ events, done }: LiveActivityProps) {
  const frame = useMemo<Frame | null>(() => humanise(events, done), [events, done]);
  if (!frame) return null;

  return (
    <div className="card flex items-center gap-3 px-4 py-2.5">
      <div className="shrink-0">
        {!done ? (
          <span className="dot-bounce inline-flex gap-1">
            <span className="size-1.5 rounded-full bg-[#0891B2]" />
            <span className="size-1.5 rounded-full bg-[#0891B2]" />
            <span className="size-1.5 rounded-full bg-[#0891B2]" />
          </span>
        ) : (
          <CheckCircle2 size={14} className="text-severity-low" />
        )}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={frame.key}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className="flex items-center gap-1.5 min-w-0 flex-1"
        >
          <frame.Icon
            size={12}
            strokeWidth={2.2}
            className={
              frame.tone === "warn"
                ? "text-severity-moderate shrink-0"
                : frame.tone === "success"
                ? "text-severity-low shrink-0"
                : "text-[#0891B2] shrink-0"
            }
          />
          <span className="text-[13px] text-foreground-muted truncate">
            {frame.text}
          </span>
          {!done && (
            <span className="caret inline-block w-[1.5px] h-3 bg-[#0891B2] shrink-0" />
          )}
        </motion.div>
      </AnimatePresence>

      {!done && (
        <span className="hidden sm:inline-block text-[10px] uppercase tracking-[0.14em] text-foreground-dim font-mono shrink-0">
          live
        </span>
      )}
    </div>
  );
}

function humanise(events: TraceEvent[], done: boolean): Frame | null {
  if (events.length === 0) {
    return { key: "init", text: "Spinning up the agent swarm…", Icon: Sparkles, tone: "info" };
  }
  if (done) {
    return { key: "done", text: "All four agents finished. Review below.", Icon: CheckCircle2, tone: "success" };
  }
  for (let i = events.length - 1; i >= 0; i--) {
    const f = describe(events[i], i);
    if (f) return f;
  }
  return { key: "thinking", text: "Thinking…", Icon: Activity, tone: "info" };
}

function describe(ev: TraceEvent, idx: number): Frame | null {
  const key = `${idx}-${ev.event_type}-${ev.agent}`;
  const tool = (ev.payload?.tool as string | undefined) ?? "";
  const args = (ev.payload?.args as Record<string, unknown> | undefined) ?? {};

  if (ev.event_type === "error") {
    return { key, text: `Error in ${prettyAgent(ev.agent)} — falling back gracefully.`, Icon: AlertCircle, tone: "warn" };
  }
  if (ev.event_type === "tool_call") {
    if (tool === "rxnorm_lookup") {
      return { key, text: `Looking up ${(args.name as string) ?? "drug"} in NIH RxNorm…`, Icon: Search, tone: "info" };
    }
    if (tool === "check_interaction") {
      return { key, text: `Checking interaction: ${(args.a as string) ?? "A"} + ${(args.b as string) ?? "B"}`, Icon: ShieldCheck, tone: "info" };
    }
    if (tool === "query_openfda") return { key, text: "Querying openFDA adverse-event reports…", Icon: Search, tone: "info" };
    if (tool === "validate_initial_state") return { key, text: "Validating input…", Icon: ShieldCheck, tone: "info" };
    if (tool === "ollama_chat_json") return { key, text: `${prettyAgent(ev.agent)} is reasoning through medications…`, Icon: Sparkles, tone: "info" };
    if (tool === "ollama_chat_text") return { key, text: "Drafting plain-English summary…", Icon: Stethoscope, tone: "info" };
    if (tool === "flesch_kincaid_grade") return { key, text: "Measuring reading level…", Icon: Activity, tone: "info" };
    if (tool === "simplify_text") return { key, text: "Simplifying — making language easier…", Icon: Wand2, tone: "info" };
    if (tool === "build_pairs") {
      const n = (args.pair_count as number) ?? 0;
      return { key, text: `Building ${n} unique drug pair${n === 1 ? "" : "s"} to analyse…`, Icon: Activity, tone: "info" };
    }
    return null;
  }
  if (ev.event_type === "enter") {
    return { key, text: `${prettyAgent(ev.agent)} woke up.`, Icon: Sparkles, tone: "info" };
  }
  if (ev.event_type === "exit") {
    return { key, text: `${prettyAgent(ev.agent)} finished${ev.duration_ms ? ` (${Math.round(ev.duration_ms)}ms)` : ""}.`, Icon: CheckCircle2, tone: "success" };
  }
  return null;
}

function prettyAgent(name: string): string {
  switch (name) {
    case "coordinator": return "Coordinator";
    case "med_parser": return "Parser";
    case "interaction_analyzer": return "Analyzer";
    case "patient_communicator": return "Communicator";
    default: return name;
  }
}
