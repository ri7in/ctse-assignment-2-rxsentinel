/**
 * Background decoration — light-mode version. Just two very subtle gradient
 * washes; no floating icons (would be busy in light mode). The page itself
 * already uses `bg-mesh` for the base; this adds depth.
 */
export function BackgroundDecor() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Very faint cyan wash top-right */}
      <div
        aria-hidden
        className="absolute -top-32 -right-32 size-[520px] rounded-full opacity-40"
        style={{
          background:
            "radial-gradient(closest-side, rgba(8,145,178,0.10), rgba(8,145,178,0) 70%)",
          filter: "blur(40px)",
        }}
      />
      {/* Very faint navy wash bottom-left */}
      <div
        aria-hidden
        className="absolute -bottom-40 -left-32 size-[520px] rounded-full opacity-30"
        style={{
          background:
            "radial-gradient(closest-side, rgba(10,14,26,0.08), rgba(10,14,26,0) 70%)",
          filter: "blur(40px)",
        }}
      />
    </div>
  );
}
