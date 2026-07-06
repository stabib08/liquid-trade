import type { Verdict } from "@/lib/types";

// Status color ALWAYS paired with an icon + text label (never color-alone).
const ICONS: Record<string, React.ReactNode> = {
  SURVIVES: (<svg viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.2 3.2L13 5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>),
  FAILED: (<svg viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>),
  INDETERMINATE: (<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.2" stroke="currentColor" strokeWidth="2" /><path d="M8 5v3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /><circle cx="8" cy="11" r="0.6" fill="currentColor" stroke="currentColor" /></svg>),
};

const LABELS: Record<string, string> = {
  SURVIVES: "Survives (for now)",
  FAILED: "Failed kill-criterion",
  INDETERMINATE: "Indeterminate",
};

export default function VerdictBadge({ verdict }: { verdict: Verdict["verdict"] }) {
  const cls = verdict.toLowerCase();
  return (
    <span className={`badge ${cls}`}>
      {ICONS[verdict]}
      {LABELS[verdict]}
    </span>
  );
}
