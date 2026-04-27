"use client";

import { useState } from "react";
import { ArrowRight, Loader2, Pill, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { submitReview } from "@/lib/api";

const EXAMPLE_INPUTS = [
  "metformin 500mg twice daily, lisinopril 10mg, ibuprofen as needed",
  "warfarin 5mg, amiodarone 200mg, digoxin 0.25mg",
  "fluoxetine 20mg, tramadol 50mg, sumatriptan 50mg",
  "simvastatin 40mg, clarithromycin 500mg twice daily, grapefruit juice every morning",
];

interface Props {
  onStart: (requestId: string) => void;
  disabled?: boolean;
}

export function MedicationForm({ onStart, disabled }: Props) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || submitting || disabled) return;
    setSubmitting(true);
    try {
      const { request_id } = await submitReview(text);
      onStart(request_id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="glass rounded-2xl p-6 md:p-8"
    >
      <div className="flex items-center gap-2 text-sm text-foreground-muted mb-3">
        <Pill size={14} className="text-[#06B6D4]" />
        <span>Paste your medication list — any format works.</span>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="metformin 500mg twice daily, lisinopril 10mg, ibuprofen as needed..."
        rows={5}
        disabled={disabled || submitting}
        className={cn(
          "w-full bg-transparent border border-white/8 rounded-xl px-4 py-3",
          "text-foreground placeholder:text-foreground-dim",
          "focus:outline-none focus:border-[#06B6D4]/50 focus:ring-2 focus:ring-[#06B6D4]/20",
          "transition-all resize-none font-mono text-sm",
          (disabled || submitting) && "opacity-50",
        )}
      />

      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLE_INPUTS.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setText(ex)}
            disabled={disabled || submitting}
            className={cn(
              "text-xs px-2.5 py-1 rounded-full border border-white/8",
              "hover:bg-white/5 hover:border-white/15 transition",
              "text-foreground-muted hover:text-foreground",
              "disabled:opacity-50 disabled:pointer-events-none",
            )}
          >
            {ex.split(",")[0].trim()} +{ex.split(",").length - 1}
          </button>
        ))}
      </div>

      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="text-xs text-foreground-dim">
          <Sparkles size={12} className="inline mr-1" />
          Runs locally via Ollama. No data leaves your machine.
        </p>
        <button
          type="submit"
          disabled={!text.trim() || submitting || disabled}
          className={cn(
            "group inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm",
            "bg-gradient-to-br from-[#06B6D4] to-[#0891B2] text-white",
            "shadow-lg shadow-[#06B6D4]/20",
            "hover:shadow-[#06B6D4]/40 hover:from-[#0CA8C9] hover:to-[#06B6D4]",
            "transition-all duration-200",
            "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-[#06B6D4]/20",
          )}
        >
          {submitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Submitting…
            </>
          ) : (
            <>
              Run safety review
              <ArrowRight
                size={16}
                className="transition-transform group-hover:translate-x-0.5"
              />
            </>
          )}
        </button>
      </div>
    </motion.form>
  );
}
