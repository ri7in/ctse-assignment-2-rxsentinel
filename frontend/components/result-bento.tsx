"use client";

import { motion } from "framer-motion";
import { FileText, ShieldCheck, Activity, Pill as PillIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FinalReport } from "@/lib/api";
import { SeverityBadge } from "@/components/severity-badge";

export function ResultBento({ report }: { report: FinalReport }) {
  const { high, moderate, low } = report.severity_summary;
  const total = high + moderate + low;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="grid grid-cols-12 gap-4"
    >
      {/* Severity dial */}
      <div className="col-span-12 md:col-span-4 glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-foreground-muted text-xs uppercase tracking-wider mb-3">
          <ShieldCheck size={14} /> Severity
        </div>
        <div className="flex items-center justify-center py-4">
          <SeverityDial high={high} moderate={moderate} low={low} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-1 text-center">
          <Stat label="High" count={high} color="text-rose-300" />
          <Stat label="Moderate" count={moderate} color="text-amber-300" />
          <Stat label="Low" count={low} color="text-emerald-300" />
        </div>
        <p className="text-xs text-foreground-dim mt-4 text-center">
          {total === 0
            ? "No interactions detected."
            : `${total} interaction${total === 1 ? "" : "s"} reviewed`}
        </p>
      </div>

      {/* Medications card */}
      <div className="col-span-12 md:col-span-8 glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-foreground-muted text-xs uppercase tracking-wider mb-3">
          <PillIcon size={14} /> Medications parsed ({report.medications.length})
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {report.medications.map((m, i) => (
            <div
              key={`${m.normalized_name}-${i}`}
              className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-foreground">
                  {m.normalized_name}
                </span>
                <span className="font-mono text-[10px] text-foreground-dim">
                  rxcui {m.rxcui ?? "?"}
                </span>
              </div>
              <div className="text-xs text-foreground-muted mt-0.5">
                {[m.dose, m.frequency, m.route].filter(Boolean).join(" · ") || "—"}
              </div>
              <div className="mt-1.5 h-1 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#06B6D4] to-[#0891B2]"
                  style={{ width: `${Math.round(m.confidence * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        {report.unparsed_terms.length > 0 && (
          <div className="mt-4 text-xs text-amber-300/80">
            Unparsed: {report.unparsed_terms.join(", ")}
          </div>
        )}
      </div>

      {/* Interactions */}
      <div className="col-span-12 glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-foreground-muted text-xs uppercase tracking-wider mb-4">
          <Activity size={14} /> Interactions ({report.interactions.length})
        </div>
        {report.interactions.length === 0 ? (
          <p className="text-sm text-foreground-dim">
            No drug-drug interactions detected by either openFDA or the local DB.
          </p>
        ) : (
          <div className="space-y-3">
            {report.interactions
              .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
              .map((it, idx) => (
                <InteractionRow key={idx} it={it} />
              ))}
          </div>
        )}
      </div>

      {/* Patient summary */}
      <div className="col-span-12 md:col-span-8 glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-foreground-muted text-xs uppercase tracking-wider">
            <FileText size={14} /> Patient summary
          </div>
          <span className="text-[11px] text-foreground-dim font-mono">
            grade {report.readability_grade.toFixed(1)}
          </span>
        </div>
        <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap text-foreground-muted leading-relaxed">
          {report.patient_summary}
        </div>
      </div>

      {/* Limitations */}
      <div className="col-span-12 md:col-span-4 glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-foreground-muted text-xs uppercase tracking-wider mb-3">
          Limitations
        </div>
        <ul className="space-y-2 text-xs text-foreground-dim leading-relaxed">
          {report.limitations.map((l, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-foreground-dim">·</span>
              <span>{l}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="font-mono text-[11px] text-foreground-dim flex justify-between">
            <span>request</span>
            <span>{report.request_id.slice(0, 8)}…</span>
          </div>
          <div className="font-mono text-[11px] text-foreground-dim flex justify-between mt-1">
            <span>duration</span>
            <span>{Math.round(report.duration_ms)}ms</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function severityRank(s: "high" | "moderate" | "low"): number {
  return s === "high" ? 0 : s === "moderate" ? 1 : 2;
}

function Stat({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div>
      <div className={cn("text-2xl font-bold tabular-nums", color)}>{count}</div>
      <div className="text-[10px] uppercase tracking-wider text-foreground-dim">{label}</div>
    </div>
  );
}

function SeverityDial({ high, moderate, low }: { high: number; moderate: number; low: number }) {
  const total = high + moderate + low || 1;
  const pct = (n: number) => (n / total) * 100;
  return (
    <div className="relative size-32">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle cx="50" cy="50" r="40" stroke="rgba(255,255,255,0.05)" strokeWidth="10" fill="none" />
        <DialArc dasharray={`${pct(high)} 100`} dashoffset="0" stroke="#f43f5e" />
        <DialArc dasharray={`${pct(moderate)} 100`} dashoffset={`-${pct(high)}`} stroke="#f59e0b" />
        <DialArc dasharray={`${pct(low)} 100`} dashoffset={`-${pct(high) + pct(moderate)}`} stroke="#10b981" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-2xl font-bold tabular-nums text-foreground">
          {high + moderate + low}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-foreground-dim">
          findings
        </span>
      </div>
    </div>
  );
}

function DialArc({
  dasharray,
  dashoffset,
  stroke,
}: {
  dasharray: string;
  dashoffset: string;
  stroke: string;
}) {
  return (
    <circle
      cx="50"
      cy="50"
      r="40"
      stroke={stroke}
      strokeWidth="10"
      fill="none"
      strokeDasharray={dasharray.split(" ").map((v) => `${(Number(v) * 2 * Math.PI * 40) / 100}`).join(" ")}
      strokeDashoffset={`${(Number(dashoffset) * 2 * Math.PI * 40) / 100}`}
      strokeLinecap="round"
    />
  );
}

function InteractionRow({ it }: { it: import("@/lib/api").Interaction }) {
  const glow =
    it.severity === "high" ? "glow-high" : it.severity === "moderate" ? "glow-moderate" : "glow-low";
  return (
    <div className={cn("rounded-xl border border-white/5 bg-white/[0.02] p-4", glow)}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground">{it.drug_a_name}</span>
            <span className="text-foreground-dim">+</span>
            <span className="font-semibold text-foreground">{it.drug_b_name}</span>
            <SeverityBadge severity={it.severity} />
          </div>
          <p className="text-sm text-foreground-muted mt-1">{it.clinical_effect}</p>
        </div>
        <div className="flex gap-1">
          {it.source.map((s) => (
            <span
              key={s}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/8 text-foreground-dim"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div>
          <div className="text-foreground-dim uppercase tracking-wider text-[10px] mb-0.5">
            Mechanism
          </div>
          <div className="text-foreground-muted">{it.mechanism}</div>
        </div>
        <div>
          <div className="text-foreground-dim uppercase tracking-wider text-[10px] mb-0.5">
            Recommendation
          </div>
          <div className="text-foreground-muted">{it.recommendation}</div>
        </div>
      </div>
    </div>
  );
}
