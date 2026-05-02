"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Loader2, Pill, Wand2, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { submitReview } from "@/lib/api";

const EXAMPLE =
  "warfarin 5mg daily, amiodarone 200mg twice daily, ibuprofen 400mg as needed, simvastatin 40mg, clarithromycin 500mg twice daily";

type Phase = "idle" | "submitting" | "running" | "done";

interface Props {
  onStart: (requestId: string) => void;
  phase: Phase;
}

export function MedicationForm({ onStart, phase }: Props) {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const locked = phase !== "idle";

  // Cmd/Ctrl + Enter to submit, regardless of focus.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (!locked && text.trim()) doSubmit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, text]);

  async function doSubmit() {
    try {
      const { request_id } = await submitReview(text);
      onStart(request_id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Submission failed");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (locked || !text.trim()) return;
    doSubmit();
  }

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "card overflow-hidden transition-all duration-200",
        locked && "border-[#A5F3FC] bg-primary-soft/30",
      )}
    >
      {/* Header row inside the card */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-subtle">
        <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] text-foreground-muted">
          <Pill size={12} className="text-[#0891B2]" />
          Medications
        </span>
        <kbd className="hidden sm:inline-block">⌘ ↵ to run</kbd>
      </div>

      <textarea
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="metformin 500mg twice daily, lisinopril 10mg, ibuprofen as needed…"
        rows={4}
        disabled={locked}
        autoFocus
        className={cn(
          "w-full bg-transparent border-0 outline-none resize-none",
          "px-4 py-4 text-base leading-relaxed",
          "placeholder:text-foreground-dim",
          "font-mono",
          locked && "opacity-60",
        )}
      />

      <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-border-subtle bg-surface-2/40">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setText(EXAMPLE)}
            disabled={locked}
            className={cn(
              "inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md",
              "border border-border hover:border-foreground-dim hover:bg-surface-2",
              "text-foreground-muted hover:text-foreground transition",
              "disabled:opacity-50 disabled:pointer-events-none",
            )}
          >
            <Wand2 size={11} />
            Try example
          </button>
          {!locked && (
            <span className="text-[11px] text-foreground-dim">
              Free-form. Brand names, generic, misspellings — all fine.
            </span>
          )}
        </div>

        <SubmitButton phase={phase} disabled={!text.trim()} />
      </div>
    </motion.form>
  );
}

function SubmitButton({ phase, disabled }: { phase: Phase; disabled: boolean }) {
  const isIdle = phase === "idle";
  const label =
    phase === "idle"
      ? "Run review"
      : phase === "submitting"
      ? "Starting…"
      : phase === "running"
      ? "Working…"
      : "Done";

  const Icon =
    phase === "idle"
      ? ArrowRight
      : phase === "done"
      ? CheckCircle2
      : Loader2;

  const iconClass = phase === "running" || phase === "submitting" ? "animate-spin" : "";

  return (
    <button
      type="submit"
      disabled={!isIdle || disabled}
      className={cn(
        "group inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md font-medium text-sm",
        "transition-all duration-150",
        phase === "idle" &&
          "bg-foreground text-background hover:bg-foreground-muted disabled:opacity-30 disabled:cursor-not-allowed",
        phase === "submitting" &&
          "bg-foreground text-background opacity-80 cursor-wait",
        phase === "running" &&
          "bg-primary-soft text-primary border border-primary-border cursor-wait",
        phase === "done" &&
          "bg-severity-low-bg text-severity-low border border-severity-low-border",
      )}
    >
      <span>{label}</span>
      <Icon
        size={14}
        className={cn(
          iconClass,
          phase === "idle" && "transition-transform group-hover:translate-x-0.5",
        )}
      />
    </button>
  );
}
