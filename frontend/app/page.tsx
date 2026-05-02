"use client";

import { useEffect, useRef, useState } from "react";
import { Github, Lock, Cpu, Zap, ArrowDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Logo } from "@/components/logo";
import { MedicationForm } from "@/components/medication-form";
import { AgentPipeline } from "@/components/agent-pipeline";
import { ResultBento } from "@/components/result-bento";
import { TraceViewer } from "@/components/trace-viewer";
import { LiveActivity } from "@/components/live-activity";
import { BackgroundDecor } from "@/components/background-decor";
import {
  type FinalReport,
  type TraceEvent,
  fetchReport,
  openTraceStream,
} from "@/lib/api";

type Phase = "idle" | "submitting" | "running" | "done";

export default function Home() {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [report, setReport] = useState<FinalReport | null>(null);
  const closerRef = useRef<(() => void) | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  const phase: Phase = report
    ? "done"
    : requestId
    ? events.length === 0
      ? "submitting"
      : "running"
    : "idle";

  // Open trace stream + poll report when a run starts.
  useEffect(() => {
    if (!requestId) return;
    setEvents([]);
    setReport(null);

    closerRef.current?.();
    closerRef.current = openTraceStream(requestId, (ev) => {
      setEvents((prev) => [...prev, ev]);
    });

    let cancelled = false;
    let attempts = 0;
    const poll = async () => {
      while (!cancelled && attempts < 60) {
        attempts += 1;
        const r = await fetchReport(requestId).catch(() => null);
        if (r) {
          setReport(r);
          return;
        }
        await new Promise((res) => setTimeout(res, 1000));
      }
    };
    poll();

    return () => {
      cancelled = true;
      closerRef.current?.();
    };
  }, [requestId]);

  // Auto-scroll to results when the report arrives — this is the missing
  // "you finished!" feedback the user complained about.
  useEffect(() => {
    if (report && resultsRef.current) {
      // Tiny delay so the card has time to render before we scroll.
      const t = setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
      return () => clearTimeout(t);
    }
  }, [report]);

  function handleNewRun() {
    setRequestId(null);
    setEvents([]);
    setReport(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="min-h-screen relative">
      <BackgroundDecor />

      {/* Tight sticky header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-5 h-12 flex items-center justify-between">
          <Logo size={22} withWordmark />
          <div className="flex items-center gap-1.5 text-xs">
            {phase !== "idle" && (
              <button
                onClick={handleNewRun}
                className="px-2.5 py-1 rounded-md text-foreground-muted hover:text-foreground hover:bg-surface-2 transition"
              >
                New review
              </button>
            )}
            <a
              href="https://github.com/ri7in/ctse-assignment-2-rxsentinel"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-foreground-muted hover:text-foreground hover:bg-surface-2 transition"
            >
              <Github size={12} /> Repo
            </a>
          </div>
        </div>
      </header>

      <section className="max-w-3xl mx-auto px-5 pt-14 md:pt-20 pb-10">
        {/* Hero — short, professional */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="text-center mb-8"
        >
          <h1 className="text-3xl md:text-[42px] font-semibold tracking-tight leading-[1.1] text-foreground">
            Medication safety review,
            <br />
            <span className="text-[#0891B2]">in plain English.</span>
          </h1>
          <p className="mt-3 text-foreground-muted text-sm md:text-base max-w-md mx-auto">
            Paste a medication list. Four local agents check for interactions,
            severity, and explain it for you.
          </p>
        </motion.div>

        {/* Form is the focal point */}
        <MedicationForm onStart={setRequestId} phase={phase} />

        {/* Trust strip — three short signals */}
        {phase === "idle" && (
          <div className="mt-4 flex items-center justify-center gap-5 text-[11px] text-foreground-dim">
            <span className="inline-flex items-center gap-1"><Lock size={11} /> Local only</span>
            <span className="inline-flex items-center gap-1"><Cpu size={11} /> Ollama (qwen2.5:3b)</span>
            <span className="inline-flex items-center gap-1"><Zap size={11} /> Free, no keys</span>
          </div>
        )}

        {/* Live activity + pipeline — appears when a run is in flight */}
        <AnimatePresence>
          {requestId && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-6 space-y-3"
            >
              <LiveActivity events={events} done={!!report} />
              <AgentPipeline events={events} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* "Done — see results" callout when finished but user hasn't scrolled */}
        <AnimatePresence>
          {report && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="mt-6 flex items-center justify-center"
            >
              <button
                onClick={() =>
                  resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
                className="inline-flex items-center gap-2 text-xs text-[#0891B2] hover:text-[#0E7490] transition"
              >
                Jump to results
                <ArrowDown size={12} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Trace viewer (collapsed by default, available after a run starts) */}
        {requestId && (
          <div className="mt-3">
            <TraceViewer events={events} />
          </div>
        )}
      </section>

      {/* Results — wider container so the bento has room. Auto-scrolled to. */}
      {report && (
        <section
          ref={resultsRef}
          className="max-w-5xl mx-auto px-5 pb-16 rise-in"
          aria-label="Review results"
        >
          <ResultBento report={report} />
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-border bg-background/60">
        <div className="max-w-5xl mx-auto px-5 py-5 flex items-center justify-between flex-wrap gap-3 text-[11px] text-foreground-dim">
          <span>
            Educational decision-support — not a substitute for professional medical advice.
          </span>
          <span className="font-mono">SE4010 · CTSE · 2026</span>
        </div>
      </footer>
    </main>
  );
}
