/**
 * Formatting utilities for medication and interaction display.
 */
import type { Medication } from "@/lib/api";

export function formatMedicationLine(m: Medication): string {
  const parts = [m.normalized_name];
  if (m.dose) parts.push(m.dose);
  if (m.frequency) parts.push(m.frequency);
  return parts.join(" · ");
}

export function formatRxCui(rxcui: string | null): string {
  return rxcui ? `rxcui ${rxcui}` : "rxcui ?";
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatConfidence(c: number): string {
  return `${Math.round(c * 100)}%`;
}
