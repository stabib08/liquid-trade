"use client";
import type { Basket } from "@/lib/types";
import { pct, signedPct, num } from "@/lib/format";
import VerdictBadge from "./VerdictBadge";
import LineChart from "./LineChart";

function Stat({ k, v, tone }: { k: string; v: string; tone?: "pos" | "neg" }) {
  return (
    <div className="stat">
      <div className="k">{k}</div>
      <div className={`v mono ${tone ?? ""}`}>{v}</div>
    </div>
  );
}

function Callout({ label, children, accent }: { label: string; children: React.ReactNode; accent: string }) {
  return (
    <div style={{ borderLeft: `3px solid ${accent}`, paddingLeft: 12, margin: "10px 0" }}>
      <div className="eyebrow" style={{ marginBottom: 2 }}>{label}</div>
      <div className="secondary" style={{ fontSize: 13.5 }}>{children}</div>
    </div>
  );
}

export default function ThesisCard({ b }: { b: Basket }) {
  const p = b.performance;
  const comp = b.factors.comparator;
  const compBeta = comp.betas?.["Comparator"];
  const compT = comp.tstats?.["Comparator"];
  const rb = b.factors.rolling_comparator_beta_latest;

  const eq = b.equity_curves;
  const betaS = b.rolling_beta_series;

  // thematic betas table rows (factor: beta, t)
  const th = b.factors.thematic;
  const thRows = th.betas ? Object.keys(th.betas) : [];

  return (
    <section className="card" id={b.id} style={{ scrollMarginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 21 }}>{b.name}</h2>
          {b.speculative && <span className="badge speculative">speculative sleeve</span>}
          <span className="mono muted" style={{ fontSize: 12.5 }}>{b.constituents.join(" · ")}</span>
        </div>
        <VerdictBadge verdict={b.verdict.verdict} />
      </div>

      <p className="secondary" style={{ fontSize: 14.5, marginTop: 10 }}>{b.thesis}</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }} className="callouts">
        <Callout label="Falsifiable prediction" accent="var(--series-1)">{b.falsifiable_prediction}</Callout>
        <Callout label="Kill-criterion" accent="var(--critical)">{b.kill_criterion}</Callout>
      </div>

      {/* verdict interpretation — the headline conclusion */}
      <div style={{ background: "var(--surface-2)", borderRadius: 10, padding: "14px 16px", margin: "12px 0" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
          <span className="eyebrow">Verdict · {b.verdict.headline}</span>
        </div>
        <p style={{ margin: 0, fontSize: 14 }}>{b.verdict.interpretation}</p>
        {b.verdict.evidence.length > 0 && (
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12.5 }} className="secondary mono">
            {b.verdict.evidence.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        )}
        {b.verdict.untestable_now.length > 0 && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            ⚠ Not yet testable: {b.verdict.untestable_now.join(" ")}
          </div>
        )}
      </div>

      {/* stat tiles: basket */}
      <div className="stat-row" style={{ margin: "6px 0 16px" }}>
        <Stat k="Ann. return" v={signedPct(p.basket.annualized_return)} tone={(p.basket.annualized_return ?? 0) >= 0 ? "pos" : "neg"} />
        <Stat k="Ann. vol" v={pct(p.basket.annualized_vol)} />
        <Stat k="Sharpe" v={num(p.basket.sharpe)} />
        <Stat k="Max DD" v={pct(p.basket.max_drawdown)} tone="neg" />
        <Stat k={`Vol vs ${b.natural_comparator}`} v={p.vol_ratio_vs_comparator ? `${num(p.vol_ratio_vs_comparator)}×` : "–"} />
        <Stat k="Eff. # names" v={num(b.effective_n, 1)} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: betaS ? "1fr 1fr" : "1fr", gap: 20 }} className="charts">
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Growth of $1 (log) — basket vs {b.primary_benchmark} vs {b.natural_comparator}</div>
          <LineChart
            dates={eq.dates}
            logCurve
            yFormat={(v) => `$${v.toFixed(v < 10 ? 1 : 0)}`}
            series={[
              { label: "Basket", color: "var(--series-1)", values: eq.basket },
              { label: b.primary_benchmark, color: "var(--series-2)", values: eq.benchmark },
              { label: b.natural_comparator, color: "var(--series-3)", values: eq.comparator },
            ]}
          />
        </div>
        {betaS && (
          <div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Rolling 126-day β to {b.natural_comparator} (95% CI). Kill-test: is β distinguishable from 1?</div>
            <LineChart
              dates={betaS.dates}
              yFormat={(v) => v.toFixed(2)}
              refLine={{ y: 1, label: "β = 1" }}
              band={{ low: betaS.ci_low, high: betaS.ci_high }}
              series={[{ label: `β to ${b.natural_comparator}`, color: "var(--series-1)", values: betaS.beta }]}
            />
          </div>
        )}
      </div>

      {/* factor table */}
      <div style={{ marginTop: 18 }}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          Factor exposure — thematic ETF set · HAC t-stats · {th.n_obs?.toLocaleString()} obs · R²={num(th.r2)}
        </div>
        <table className="tab">
          <thead>
            <tr><th>Factor</th><th>β</th><th>t-stat</th><th>Read</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Alpha (annual)</td>
              <td className="mono">{signedPct(th.alpha_annual)}</td>
              <td className={`mono ${Math.abs(th.alpha_tstat ?? 0) > 2 ? "sig" : ""}`}>{num(th.alpha_tstat)}</td>
              <td className="muted" style={{ textAlign: "left", fontSize: 12 }}>{Math.abs(th.alpha_tstat ?? 0) > 2 ? "significant" : "not significant"}</td>
            </tr>
            {thRows.map((f) => (
              <tr key={f}>
                <td>{f}</td>
                <td className="mono">{num(th.betas![f])}</td>
                <td className={`mono ${Math.abs(th.tstats?.[f] ?? 0) > 2 ? "sig" : ""}`}>{num(th.tstats?.[f])}</td>
                <td className="muted" style={{ textAlign: "left", fontSize: 12 }}>{Math.abs(th.tstats?.[f] ?? 0) > 2 ? "loads" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
          Comparator-controlled: β to {b.natural_comparator} = <span className="mono">{num(compBeta)}</span> (t=<span className="mono">{num(compT)}</span>),
          market-controlled alpha = <span className="mono">{signedPct(comp.alpha_annual)}</span> (t=<span className="mono">{num(comp.alpha_tstat)}</span>).
          {rb && <> Latest rolling β = <span className="mono">{num(rb.beta)}</span>, CI [{num(rb.ci_low)}, {num(rb.ci_high)}] — {rb.ci_low <= 1 && 1 <= rb.ci_high ? "contains 1.0" : "excludes 1.0"}.</>}
        </div>
      </div>
    </section>
  );
}
