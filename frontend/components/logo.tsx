import { cn } from "@/lib/utils";

interface LogoProps {
  size?: number;
  className?: string;
  withWordmark?: boolean;
}

export function Logo({ size = 28, className, withWordmark = false }: LogoProps) {
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
        <path
          d="M32 3 L57 13 V32 Q57 51 32 61 Q7 51 7 32 V13 Z"
          stroke="#0891B2"
          strokeWidth="3.2"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M22 19 L22 47 M22 19 L31 19 Q36 19 36 24.5 Q36 30 31 30 L22 30"
          stroke="#0891B2"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M30 30 L43 47"
          stroke="#0891B2"
          strokeWidth="3.2"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M34 33 L40 39"
          stroke="#0891B2"
          strokeWidth="3.2"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      {withWordmark && (
        <span className="font-semibold tracking-tight text-[15px] text-foreground">
          <span className="text-[#0891B2]">Rx</span>Sentinel
        </span>
      )}
    </div>
  );
}
