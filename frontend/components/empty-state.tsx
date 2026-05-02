import { Sparkles } from "lucide-react";

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="card p-10 flex flex-col items-center justify-center text-center">
      <Sparkles size={24} className="text-[#0891B2] mb-3" />
      <p className="text-foreground-muted text-sm">{message}</p>
    </div>
  );
}
