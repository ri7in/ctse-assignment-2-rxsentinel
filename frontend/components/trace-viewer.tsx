"use client";

import { useState } from "react";
import { ChevronDown, Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/lib/api";

const EVENT_COLOR: Record<TraceEvent["event_type"], string> = {
  enter: "text-cyan-300",
  exit: "text-emerald-300",
  tool_call: "text-amber-300",
  tool_result: "text-amber-300/70",
  error: "text-rose-300",
  llm_token: "text-foreground-dim",
};

export function TraceViewer({ events }: { events: TraceEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="glass rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/3 transition"
      >
        <span className="flex items-center gap-2 text-sm text-foreground-muted">
          <Terminal size={14} /> Trace ({events.length} events)
        </span>
        <ChevronDown
          size={16}
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
            className="overflow-hidden border-t border-white/5"
          >
            <div className="max-h-96 overflow-auto px-5 py-3 font-mono text-[11px] leading-relaxed">
              {events.map((ev, i) => (
                <div key={i} className="flex gap-2 py-0.5">
                  <span className="text-foreground-dim shrink-0">
                    {new Date(ev.ts).toLocaleTimeString()}
                  </span>
                  <span className={cn("shrink-0 w-32 truncate", EVENT_COLOR[ev.event_type])}>
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
