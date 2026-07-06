"use client";
// Cross-basket correlation heatmap. Correlations here are all positive (0–1), so
// a single-hue SEQUENTIAL blue ramp is correct (light = near zero, dark = strong).
import { useState } from "react";

const RAMP = [
  { t: 0.0, c: "var(--seq-100)" },
  { t: 0.35, c: "var(--seq-250)" },
  { t: 0.6, c: "var(--seq-400)" },
  { t: 0.8, c: "var(--seq-550)" },
  { t: 1.0, c: "var(--seq-700)" },
];

function shade(v: number): string {
  const x = Math.max(0, Math.min(1, v));
  let stop = RAMP[0];
  for (const s of RAMP) if (x >= s.t) stop = s;
  return stop.c;
}

export default function Heatmap({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  const [hi, setHi] = useState<[number, number] | null>(null);
  const short = labels.map((l) => l.replace(/_/g, " "));
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "separate", borderSpacing: 2, fontSize: 12 }}>
        <thead>
          <tr>
            <th></th>
            {short.map((l) => (
              <th key={l} style={{ padding: "4px 6px", color: "var(--text-muted)", fontWeight: 600, fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.03em", writingMode: "horizontal-tb" }}>{l}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td style={{ padding: "4px 8px", color: "var(--text-secondary)", fontWeight: 600, whiteSpace: "nowrap" }}>{short[i]}</td>
              {row.map((v, j) => {
                const strong = v > 0.7;
                return (
                  <td key={j}
                      onMouseEnter={() => setHi([i, j])} onMouseLeave={() => setHi(null)}
                      title={`${short[i]} × ${short[j]} = ${v.toFixed(2)}`}
                      style={{
                        background: shade(v), color: strong ? "#fff" : "var(--text-primary)",
                        textAlign: "center", width: 62, height: 40, borderRadius: 6,
                        fontWeight: i === j ? 700 : 600, cursor: "default",
                        outline: hi && hi[0] === i && hi[1] === j ? "2px solid var(--text-primary)" : "none",
                        fontVariantNumeric: "tabular-nums",
                      }}>
                    {v.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
