/**
 * Severity helpers shared across components.
 */
import type { Severity } from "@/lib/api";

const RANK: Record<Severity, number> = { high: 0, moderate: 1, low: 2 };

export function severityRank(s: Severity): number {
  return RANK[s];
}

export function compareBySeverity(a: { severity: Severity }, b: { severity: Severity }): number {
  return severityRank(a.severity) - severityRank(b.severity);
}

export function severityClass(s: Severity): string {
  return s === "high" ? "glow-high" : s === "moderate" ? "glow-moderate" : "glow-low";
}

export function severityLabel(s: Severity): string {
  return s === "high" ? "High" : s === "moderate" ? "Moderate" : "Low";
}
