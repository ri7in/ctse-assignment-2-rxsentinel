import { cn } from "@/lib/utils";

interface LogoProps {
  size?: number;
  className?: string;
  withWordmark?: boolean;
}

export function Logo({ size = 36, className, withWordmark = false }: LogoProps) {
  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 64 64"
        fill="none"
        width={size}
        height={size}
        aria-label="RxSentinel"
      >
        <defs>
          <linearGradient id="rx-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#0891B2" />
          </linearGradient>
        </defs>
        <path
          d="M32 3 L57 13 V32 Q57 51 32 61 Q7 51 7 32 V13 Z"
          stroke="url(#rx-grad)"
          strokeWidth="3"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M22 19 L22 47 M22 19 L31 19 Q36 19 36 24.5 Q36 30 31 30 L22 30"
          stroke="url(#rx-grad)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M30 30 L43 47"
          stroke="url(#rx-grad)"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M34 33 L40 39"
          stroke="url(#rx-grad)"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      {withWordmark && (
        <span className="font-bold tracking-tight text-xl">
          <span className="bg-gradient-to-br from-[#06B6D4] to-[#0891B2] bg-clip-text text-transparent">
            Rx
          </span>
          <span className="text-foreground">Sentinel</span>
        </span>
      )}
    </div>
  );
}
