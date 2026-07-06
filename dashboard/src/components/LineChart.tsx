"use client";
import { useRef, useState } from "react";

export interface LineSeries {
  label: string;
  color: string;      // CSS var reference, e.g. "var(--series-1)"
  values: number[];
}

interface Props {
  dates: string[];
  series: LineSeries[];
  height?: number;
  yFormat?: (v: number) => string;
  title?: string;
  // optional horizontal reference line (e.g. beta = 1.0)
  refLine?: { y: number; label: string };
  // optional shaded band (e.g. CI): low/high per point, drawn under series[0]
  band?: { low: number[]; high: number[] };
  logCurve?: boolean; // for growth-of-$1, plot on log scale
}

const PAD = { t: 14, r: 54, b: 22, l: 44 };

export default function LineChart({
  dates, series, height = 240, yFormat = (v) => v.toFixed(2),
  refLine, band, logCurve = false,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = height;
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b;

  const tx = (v: number) => (logCurve ? Math.log(Math.max(v, 1e-6)) : v);
  const all: number[] = [];
  series.forEach((s) => s.values.forEach((v) => Number.isFinite(v) && all.push(tx(v))));
  if (band) { band.low.forEach((v) => Number.isFinite(v) && all.push(tx(v))); band.high.forEach((v) => Number.isFinite(v) && all.push(tx(v))); }
  if (refLine) all.push(tx(refLine.y));
  let lo = Math.min(...all), hi = Math.max(...all);
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo === hi) { lo -= 1; hi += 1; }
  const padY = (hi - lo) * 0.06; lo -= padY; hi += padY;

  const n = dates.length;
  const X = (i: number) => PAD.l + (n <= 1 ? 0 : (i / (n - 1)) * iw);
  const Y = (v: number) => PAD.t + ih - ((tx(v) - lo) / (hi - lo)) * ih;

  const path = (vals: number[]) => {
    let d = "", started = false;
    vals.forEach((v, i) => {
      if (!Number.isFinite(v)) return;
      d += `${started ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)} `;
      started = true;
    });
    return d;
  };

  // y ticks (4)
  const ticks = Array.from({ length: 4 }, (_, k) => lo + ((k + 1) / 4) * (hi - lo));
  const invTx = (t: number) => (logCurve ? Math.exp(t) : t);

  const onMove = (e: React.MouseEvent) => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.l) / iw) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, i)));
  };

  const bandPath = band
    ? `${band.high.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join(" ")} ` +
      `${band.low.map((v, i) => `L${X(band.low.length - 1 - i).toFixed(1)} ${Y(band.low[band.low.length - 1 - i]).toFixed(1)}`).join(" ")} Z`
    : "";

  return (
    <div>
      <div className="legend" style={{ marginBottom: 8 }}>
        {series.map((s) => (
          <span className="item" key={s.label}>
            <span className="swatch" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
        {refLine && (
          <span className="item"><span className="swatch" style={{ background: "var(--text-muted)", height: 0, borderTop: "2px dashed var(--text-muted)" }} />{refLine.label}</span>
        )}
      </div>
      <div ref={wrapRef} style={{ position: "relative", width: "100%" }}
           onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" preserveAspectRatio="xMidYMid meet"
             role="img" style={{ display: "block" }}>
          {/* gridlines */}
          {ticks.map((t, k) => (
            <g key={k}>
              <line x1={PAD.l} x2={W - PAD.r} y1={Y(invTx(t))} y2={Y(invTx(t))} stroke="var(--grid)" strokeWidth={1} />
              <text x={PAD.l - 6} y={Y(invTx(t)) + 3} textAnchor="end" fontSize={10} fill="var(--text-muted)" className="mono">{yFormat(invTx(t))}</text>
            </g>
          ))}
          {/* CI band */}
          {band && <path d={bandPath} fill="var(--series-1-soft)" stroke="none" />}
          {/* reference line */}
          {refLine && (
            <line x1={PAD.l} x2={W - PAD.r} y1={Y(refLine.y)} y2={Y(refLine.y)}
                  stroke="var(--text-muted)" strokeWidth={1.5} strokeDasharray="4 4" />
          )}
          {/* series */}
          {series.map((s) => (
            <path key={s.label} d={path(s.values)} fill="none" stroke={s.color}
                  strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          ))}
          {/* direct end labels (relief rule: identity never color-alone) */}
          {series.map((s) => {
            const li = [...s.values].map((v, i) => (Number.isFinite(v) ? i : -1)).filter((i) => i >= 0).pop();
            if (li === undefined) return null;
            return (
              <text key={s.label} x={X(li) + 5} y={Y(s.values[li]) + 3} fontSize={10.5}
                    fill={s.color} fontWeight={700}>{s.label}</text>
            );
          })}
          {/* hover crosshair */}
          {hover !== null && (
            <g>
              <line x1={X(hover)} x2={X(hover)} y1={PAD.t} y2={PAD.t + ih} stroke="var(--axis)" strokeWidth={1} />
              {series.map((s) => Number.isFinite(s.values[hover]) && (
                <circle key={s.label} cx={X(hover)} cy={Y(s.values[hover])} r={3.5} fill={s.color} stroke="var(--surface-1)" strokeWidth={1.5} />
              ))}
            </g>
          )}
          {/* x labels: first & last */}
          <text x={PAD.l} y={H - 6} fontSize={10} fill="var(--text-muted)">{dates[0]}</text>
          <text x={W - PAD.r} y={H - 6} fontSize={10} fill="var(--text-muted)" textAnchor="end">{dates[n - 1]}</text>
        </svg>
        {hover !== null && (
          <div style={{
            position: "absolute", top: 4, left: `${(X(hover) / W) * 100}%`,
            transform: `translateX(${hover > n / 2 ? "-105%" : "8px"})`,
            background: "var(--surface-1)", border: "1px solid var(--border)",
            borderRadius: 8, padding: "6px 9px", fontSize: 11.5, pointerEvents: "none",
            boxShadow: "0 4px 14px rgba(0,0,0,0.12)", whiteSpace: "nowrap", zIndex: 3,
          }}>
            <div className="muted" style={{ marginBottom: 3 }}>{dates[hover]}</div>
            {series.map((s) => (
              <div key={s.label} style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
                <span style={{ color: s.color, fontWeight: 700 }}>{s.label}</span>
                <span className="mono">{Number.isFinite(s.values[hover]) ? yFormat(s.values[hover]) : "–"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
