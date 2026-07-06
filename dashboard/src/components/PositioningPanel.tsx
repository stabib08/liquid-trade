import type { Report } from "@/lib/types";
import { pct, money } from "@/lib/format";

function CohortBar({ label, frac, color }: { label: string; frac: number | null; color: string }) {
  const w = frac === null ? 0 : Math.max(0, Math.min(1, frac)) * 100;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "3px 0" }}>
      <span style={{ width: 46, fontSize: 11, color: "var(--text-muted)" }}>{label}</span>
      <div style={{ flex: 1, height: 14, background: "var(--surface-2)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${w}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
      <span className="mono" style={{ width: 42, fontSize: 12, textAlign: "right" }}>{pct(frac, 0)}</span>
    </div>
  );
}

export default function PositioningPanel({ overlay }: { overlay: Report["positioning_overlay"] }) {
  const am = overlay.analyze_market;
  const tickers = Object.keys(am);
  return (
    <div>
      <div className="legend" style={{ marginBottom: 10 }}>
        <span className="item"><span className="swatch" style={{ background: "var(--series-1)" }} />Retail (&lt;$25k) long %</span>
        <span className="item"><span className="swatch" style={{ background: "var(--series-3)" }} />Whales (≥$250k) long %</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
        {tickers.map((t) => {
          const d = am[t];
          const div = d.smart_money_divergence;
          return (
            <div key={t} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{t}</strong>
                <span className="mono muted" style={{ fontSize: 11.5 }}>OI {money(d.open_interest_usd)} · {d.position_count} pos</span>
              </div>
              <div style={{ margin: "8px 0" }}>
                <CohortBar label="retail" frac={d.retail_long_frac} color="var(--series-1)" />
                <CohortBar label="whales" frac={d.whale_long_frac} color="var(--series-3)" />
              </div>
              <div style={{ fontSize: 12 }} className="secondary">
                Divergence: <span className="mono" style={{ fontWeight: 700, color: Math.abs(div ?? 0) > 0.2 ? "var(--series-1)" : "var(--text-muted)" }}>{div === null ? "–" : `${div > 0 ? "+" : ""}${(div * 100).toFixed(0)}pp`}</span>
                {Math.abs(div ?? 0) > 0.2 ? " — retail crowded long, whales fading" : " — cohorts aligned"}
              </div>
            </div>
          );
        })}
      </div>

      <div className="muted" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.5 }}>
        On a zero-sum perps venue aggregate long-share is ~50% <em>by construction</em>, so the
        informative signal is the <strong>retail-vs-whale dispersion</strong>, not the headline long %.
      </div>

      {overlay.pulse.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Market-wide positioning pulse — notional by symbol (deep-tech-adjacent names surface here)</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {overlay.pulse.slice(0, 12).map((p) => {
              const hot = ["SPACEX", "MU", "SKHX"].includes(p.symbol);
              return (
                <span key={p.symbol} className="mono" style={{
                  fontSize: 12, padding: "4px 9px", borderRadius: 999,
                  border: "1px solid var(--border)",
                  background: hot ? "var(--series-1-soft)" : "var(--surface-2)",
                  fontWeight: hot ? 700 : 500,
                }}>
                  {p.symbol} {money(p.notional_usd)}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
