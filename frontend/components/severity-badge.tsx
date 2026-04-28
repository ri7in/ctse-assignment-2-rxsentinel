import { AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/api";

const config: Record<
  Severity,
  { label: string; bg: string; text: string; icon: typeof AlertTriangle }
> = {
  high: {
    label: "High",
    bg: "bg-rose-500/15",
    text: "text-rose-300",
    icon: AlertTriangle,
  },
  moderate: {
    label: "Moderate",
    bg: "bg-amber-500/15",
    text: "text-amber-300",
    icon: AlertCircle,
  },
  low: {
    label: "Low",
    bg: "bg-emerald-500/15",
    text: "text-emerald-300",
    icon: CheckCircle2,
  },
};

export function SeverityBadge({
  severity,
  className,
  showLabel = true,
}: {
  severity: Severity;
  className?: string;
  showLabel?: boolean;
}) {
  const { label, bg, text, icon: Icon } = config[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border border-white/5",
        bg,
        text,
        className,
      )}
    >
      <Icon size={12} strokeWidth={2.5} />
      {showLabel && <span>{label}</span>}
    </span>
  );
}
