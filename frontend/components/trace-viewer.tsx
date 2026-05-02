"use client";

import { useState } from "react";
import { ChevronDown, Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/lib/api";

const EVENT_COLOR: Record<TraceEvent["event_type"], string> = {
  enter: "text-[#0891B2]",
  exit: "text-severity-low",
  tool_call: "text-severity-moderate",
  tool_result: "text-severity-moderate/70",
  error: "text-severity-high",
  llm_token: "text-foreground-dim",
};

export function TraceViewer({ events }: { events: TraceEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-surface-2/60 transition"
      >
        <span className="flex items-center gap-2 text-xs text-foreground-muted">
          <Terminal size={12} />
          Trace
          <span className="font-mono text-[11px] text-foreground-dim">
            {events.length} events
          </span>
        </span>
        <ChevronDown
          size={14}
          className={cn(
            "text-foreground-dim transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden border-t border-border-subtle"
          >
            <div className="max-h-96 overflow-auto px-4 py-3 font-mono text-[11px] leading-relaxed bg-surface-2/40">
              {events.map((ev, i) => (
                <div key={i} className="flex gap-2 py-0.5">
                  <span className="text-foreground-dim shrink-0 w-20 truncate">
                    {new Date(ev.ts).toLocaleTimeString()}
                  </span>
                  <span className={cn("shrink-0 w-44 truncate", EVENT_COLOR[ev.event_type])}>
                    {ev.agent}.{ev.event_type}
                  </span>
                  <span className="text-foreground-muted truncate flex-1">
                    {summarize(ev.payload)}
                    {ev.duration_ms != null && (
                      <span className="text-foreground-dim ml-2">
                        ({Math.round(ev.duration_ms)}ms)
                      </span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function summarize(payload: Record<string, unknown>): string {
  try {
    const json = JSON.stringify(payload);
    return json.length > 140 ? json.slice(0, 140) + "…" : json;
  } catch {
    return String(payload);
  }
}
