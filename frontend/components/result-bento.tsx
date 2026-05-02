"use client";

import { motion } from "framer-motion";
import {
  Stethoscope,
  HeartPulse,
  PillBottle,
  Pill as PillIcon,
  BookOpenText,
  Info,
  Hash,
  Timer,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { FinalReport, Interaction } from "@/lib/api";
import { SeverityBadge } from "@/components/severity-badge";

export function ResultBento({ report }: { report: FinalReport }) {
  const { high, moderate, low } = report.severity_summary;
  const total = high + moderate + low;
  return (
    <div className="space-y-4">
      {/* Header strip — most important info first */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="card p-5 flex items-center justify-between flex-wrap gap-4"
      >
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-foreground-muted mb-1">
            Review complete
          </div>
          <h2 className="text-xl font-semibold tracking-tight">
            {total === 0
              ? "No interactions detected"
              : `${total} interaction${total === 1 ? "" : "s"} found`}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <SeverityCount label="High"     count={high}     tone="high" />
          <SeverityCount label="Moderate" count={moderate} tone="moderate" />
          <SeverityCount label="Low"      count={low}      tone="low" />
        </div>
      </motion.div>

      {/* Two-column: medications | interactions */}
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 lg:col-span-5">
          <CardHeader Icon={PillBottle} title="Medications">
            <span className="font-mono text-[11px] text-foreground-dim">
              {report.medications.length} parsed
            </span>
          </CardHeader>
          <div className="divide-y divide-border-subtle">
            {report.medications.map((m, i) => (
              <div
                key={`${m.normalized_name}-${i}`}
                className="flex items-center justify-between gap-3 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 truncate">
                    <PillIcon size={13} className="text-[#0891B2] shrink-0" />
                    <span className="text-sm font-medium truncate">
                      {m.normalized_name}
                    </span>
                  </div>
                  <div className="text-[11px] text-foreground-muted mt-0.5 ml-[21px]">
                    {[m.dose, m.frequency, m.route].filter(Boolean).join(" · ") || "—"}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-mono text-[10px] text-foreground-dim">
                    rxcui {m.rxcui ?? "?"}
                  </div>
                  <div className="text-[10px] text-foreground-dim mt-0.5">
                    {Math.round(m.confidence * 100)}% conf.
                  </div>
                </div>
              </div>
            ))}
            {report.unparsed_terms.length > 0 && (
              <div className="px-4 py-2 text-[11px] text-severity-moderate">
                Unparsed: {report.unparsed_terms.join(", ")}
              </div>
            )}
          </div>
        </Card>

        <Card className="col-span-12 lg:col-span-7">
          <CardHeader Icon={Stethoscope} title="Interactions">
            <span className="font-mono text-[11px] text-foreground-dim">
              {report.interactions.length} found
            </span>
          </CardHeader>
          <div className="divide-y divide-border-subtle">
            {report.interactions.length === 0 ? (
              <div className="p-6 text-sm text-foreground-muted text-center">
                No drug-drug interactions detected.
              </div>
            ) : (
              [...report.interactions]
                .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
                .map((it, idx) => <InteractionRow key={idx} it={it} />)
            )}
          </div>
        </Card>
      </div>

      {/* Patient summary — full width */}
      <Card>
        <CardHeader Icon={BookOpenText} title="Plain-English summary">
          <span className="font-mono text-[11px] text-foreground-dim">
            grade {report.readability_grade.toFixed(1)}
          </span>
        </CardHeader>
        <div className="px-5 py-4 prose prose-sm max-w-none whitespace-pre-wrap text-foreground-muted leading-relaxed">
          {report.patient_summary}
        </div>
      </Card>

      {/* Meta + limitations */}
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 lg:col-span-8">
          <CardHeader Icon={Info} title="Limitations" />
          <ul className="px-5 py-4 space-y-2 text-[13px] text-foreground-muted leading-relaxed">
            {report.limitations.map((l, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-foreground-dim">·</span>
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="col-span-12 lg:col-span-4">
          <CardHeader Icon={Hash} title="Run" />
          <dl className="px-5 py-4 space-y-2 text-xs">
            <Meta label="Request" mono>{report.request_id.slice(0, 8)}…</Meta>
            <Meta label="Duration" mono>
              <span className="inline-flex items-center gap-1">
                <Timer size={11} className="text-foreground-dim" />
                {Math.round(report.duration_ms / 1000)}s
              </span>
            </Meta>
            <Meta label="Started" mono>
              {new Date(report.started_at).toLocaleTimeString()}
            </Meta>
          </dl>
        </Card>
      </div>
    </div>
  );
}

function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("card overflow-hidden", className)}>{children}</div>;
}

function CardHeader({
  Icon,
  title,
  children,
}: {
  Icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-subtle">
      <span className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-foreground-muted">
        <Icon size={12} className="text-[#0891B2]" />
        {title}
      </span>
      {children}
    </div>
  );
}

function Meta({ label, mono, children }: { label: string; mono?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-foreground-dim">{label}</dt>
      <dd className={cn(mono && "font-mono", "text-foreground")}>{children}</dd>
    </div>
  );
}

function severityRank(s: "high" | "moderate" | "low"): number {
  return s === "high" ? 0 : s === "moderate" ? 1 : 2;
}

function SeverityCount({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "high" | "moderate" | "low";
}) {
  const cls =
    tone === "high"
      ? "severity-high"
      : tone === "moderate"
      ? "severity-moderate"
      : "severity-low";
  return (
    <div
      className={cn(
        "px-3 py-2 rounded-md border min-w-[68px] text-center",
        cls,
      )}
    >
      <div className="text-2xl font-semibold tabular-nums leading-none">
        {count}
      </div>
      <div className="text-[10px] uppercase tracking-[0.14em] mt-1 opacity-80">
        {label}
      </div>
    </div>
  );
}

function InteractionRow({ it }: { it: Interaction }) {
  return (
    <div className="px-4 py-3 hover:bg-surface-2/40 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{it.drug_a_name}</span>
          <span className="text-foreground-dim">+</span>
          <span className="font-medium text-sm">{it.drug_b_name}</span>
          <SeverityBadge severity={it.severity} />
        </div>
        <div className="flex gap-1">
          {it.source.map((s) => (
            <span
              key={s}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border text-foreground-dim"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
      <p className="text-[13px] text-foreground-muted">{it.clinical_effect}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2 text-[12px]">
        <div>
          <span className="text-foreground-dim uppercase tracking-[0.14em] text-[10px] mr-1">
            Mechanism
          </span>
          <span className="text-foreground-muted">{it.mechanism}</span>
        </div>
        <div>
          <span className="text-foreground-dim uppercase tracking-[0.14em] text-[10px] mr-1">
            Action
          </span>
          <span className="text-foreground-muted">{it.recommendation}</span>
        </div>
      </div>
    </div>
  );
}
