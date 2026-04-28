import { Sparkles } from "lucide-react";

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center text-center">
      <Sparkles size={32} className="text-[#06B6D4] mb-3" />
      <p className="text-foreground-muted text-sm">{message}</p>
    </div>
  );
}
