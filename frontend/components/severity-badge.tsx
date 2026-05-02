import { AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/api";

const config: Record<
  Severity,
  { label: string; cls: string; icon: typeof AlertTriangle }
> = {
  high:     { label: "High",     cls: "severity-high",     icon: AlertTriangle },
  moderate: { label: "Moderate", cls: "severity-moderate", icon: AlertCircle  },
  low:      { label: "Low",      cls: "severity-low",      icon: CheckCircle2 },
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
  const { label, cls, icon: Icon } = config[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium border",
        cls,
        className,
      )}
    >
      <Icon size={11} strokeWidth={2.5} />
      {showLabel && <span>{label}</span>}
    </span>
  );
}
