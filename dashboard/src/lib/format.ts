// Pure formatting helpers (no server-only deps; safe in client components).
export const pct = (x?: number | null, d = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "–" : `${(x * 100).toFixed(d)}%`;
export const signedPct = (x?: number | null, d = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "–" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`;
export const num = (x?: number | null, d = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "–" : x.toFixed(d);
export const money = (x?: number | null) => {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  if (Math.abs(x) >= 1e9) return `$${(x / 1e9).toFixed(1)}B`;
  if (Math.abs(x) >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
  if (Math.abs(x) >= 1e3) return `$${(x / 1e3).toFixed(0)}K`;
  return `$${x.toFixed(0)}`;
};
