"use client";

import { useEffect, useRef, useState } from "react";
import { Github, Shield, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { Logo } from "@/components/logo";
import { MedicationForm } from "@/components/medication-form";
import { AgentPipeline } from "@/components/agent-pipeline";
import { ResultBento } from "@/components/result-bento";
import { TraceViewer } from "@/components/trace-viewer";
import {
  type FinalReport,
  type TraceEvent,
  fetchReport,
  openTraceStream,
} from "@/lib/api";

export default function Home() {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [report, setReport] = useState<FinalReport | null>(null);
  const closerRef = useRef<(() => void) | null>(null);

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

  return (
    <main className="min-h-screen">
      <header className="max-w-6xl mx-auto px-6 pt-8 pb-2 flex items-center justify-between">
        <Logo size={32} withWordmark />
        <div className="flex items-center gap-3 text-sm">
          <a
            href="https://github.com/ri7in/ctse-assignment-2-rxsentinel"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/8 hover:bg-white/5 hover:border-white/15 transition text-foreground-muted hover:text-foreground"
          >
            <Github size={14} /> GitHub
          </a>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full border border-white/8 text-foreground-muted">
            <Sparkles size={12} className="text-[#06B6D4]" />
            Multi-agent · Local · Zero-cost
          </span>
          <h1 className="mt-5 text-4xl md:text-6xl font-bold tracking-tight">
            <span className="bg-gradient-to-br from-[#06B6D4] to-[#0891B2] bg-clip-text text-transparent">
              AI agents
            </span>{" "}
            on watch for
            <br />
            medication harm.
          </h1>
          <p className="mt-4 text-foreground-muted max-w-xl mx-auto">
            Paste a list of medications. A swarm of four LangGraph agents — running
            entirely on your machine via Ollama — finds interactions, ranks
            severity, and explains it all in plain English.
          </p>
        </motion.div>

        <MedicationForm onStart={setRequestId} disabled={!!requestId && !report} />

        {requestId && (
          <div className="mt-6 space-y-4">
            <AgentPipeline events={events} />
            <TraceViewer events={events} />
          </div>
        )}

        {report && (
          <div className="mt-6">
            <ResultBento report={report} />
          </div>
        )}
      </section>

      <footer className="max-w-6xl mx-auto px-6 py-12 text-xs text-foreground-dim flex items-center gap-2">
        <Shield size={12} />
        Educational decision-support tool. Not a substitute for professional medical advice.
      </footer>
    </main>
  );
}
