import { loadReport } from "@/lib/data";
import ThesisCard from "@/components/ThesisCard";
import VerdictBadge from "@/components/VerdictBadge";
import Heatmap from "@/components/Heatmap";
import PositioningPanel from "@/components/PositioningPanel";

export default function Home() {
  const r = loadReport();
  const m = r.meta;

  return (
    <main className="wrap" style={{ padding: "36px 20px 80px" }}>
      {/* header */}
      <header style={{ marginBottom: 26 }}>
        <div className="eyebrow">liquid-trade · point-in-time quant research</div>
        <h1 style={{ fontSize: 30, margin: "6px 0 8px", lineHeight: 1.15 }}>
          Public-equity proxy baskets for private deep-tech theses
        </h1>
        <p className="secondary" style={{ fontSize: 15.5, maxWidth: 760, margin: 0 }}>
          You can&rsquo;t buy SpaceX or Anduril. So each deep-tech thesis is a public-equity
          proxy basket with a <strong>falsifiable prediction</strong> and an explicit{" "}
          <strong>kill-criterion</strong>, tracked against the benchmark that makes the
          falsification real. Several are <em>expected</em> to fail — reporting that is the point.
        </p>
        <div className="mono muted" style={{ fontSize: 12, marginTop: 12, display: "flex", flexWrap: "wrap", gap: "4px 18px" }}>
          <span>prices {m.price_dates[0]} → {m.price_dates[1]} ({m.price_source})</span>
          <span>factors {m.factor_source}</span>
          <span>{m.regression_se}</span>
          <span>weighting: {m.weighting}</span>
          <span>{m.n_ingest_runs} ingest runs · last {m.last_ingest?.slice(0, 10)}</span>
          <span>build {m.code_version ?? "dev"} · {m.generated_at.slice(0, 16).replace("T", " ")}Z</span>
        </div>
      </header>

      {/* honesty banner */}
      <div className="card" style={{ padding: "12px 16px", marginBottom: 20, fontSize: 13, borderLeft: "3px solid var(--warning)" }}>
        <strong>Read this as a falsification harness, not a claim of alpha.</strong>{" "}
        <span className="secondary">{m.assumptions_note}</span>
      </div>

      {/* theses-first summary strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 12, marginBottom: 30 }}>
        {r.baskets.map((b) => (
          <a key={b.id} href={`#${b.id}`} className="card" style={{ padding: 14, display: "block" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <strong style={{ fontSize: 15 }}>{b.name}</strong>
              {b.speculative && <span className="badge speculative" style={{ fontSize: 10 }}>spec</span>}
            </div>
            <div style={{ margin: "8px 0" }}><VerdictBadge verdict={b.verdict.verdict} /></div>
            <div className="mono muted" style={{ fontSize: 11.5 }}>{b.verdict.headline}</div>
          </a>
        ))}
      </div>

      {/* per-basket cards */}
      <div style={{ display: "grid", gap: 20 }}>
        {r.baskets.map((b) => <ThesisCard key={b.id} b={b} />)}
      </div>

      {/* cross-basket correlation */}
      <section className="card" style={{ marginTop: 20 }}>
        <div className="eyebrow">Cross-basket correlation{r.cross_basket_correlation.window && <> · {r.cross_basket_correlation.window[0]} → {r.cross_basket_correlation.window[1]} (common window)</>}</div>
        <h2 style={{ fontSize: 19, margin: "6px 0 4px" }}>Are these four distinct theses, or one big beta trade?</h2>
        <p className="secondary" style={{ fontSize: 13.5, marginTop: 0 }}>
          All pairwise correlations are positive but moderate — the baskets share a growth/risk
          factor yet are far from redundant. Quantum is the least correlated with the rest.
        </p>
        <Heatmap labels={r.cross_basket_correlation.labels} matrix={r.cross_basket_correlation.matrix} />
      </section>

      {/* positioning overlay */}
      <section className="card" style={{ marginTop: 20 }}>
        <div className="eyebrow">Positioning overlay · Co-Invest / Liquid</div>
        <h2 style={{ fontSize: 19, margin: "6px 0 4px" }}>Where is the crowd — and is smart money fading it?</h2>
        <p className="secondary" style={{ fontSize: 13.5, marginTop: 0 }}>
          Per-ticker cohort positioning for the two basket names that trade on Liquid. Captured
          via the MCP connector during interactive runs (not the headless cron).
        </p>
        <PositioningPanel overlay={r.positioning_overlay} />
      </section>

      {/* footer */}
      <footer style={{ marginTop: 30, paddingTop: 18, borderTop: "1px solid var(--border)", fontSize: 13 }} className="secondary">
        <p>
          Method &amp; provenance: <a href="https://github.com/stabib08/liquid-trade/blob/main/docs/methodology.md">methodology.md</a>{" · "}
          honest failure modes: <a href="https://github.com/stabib08/liquid-trade/blob/main/docs/limitations.md">limitations.md</a>{" · "}
          connector probe: <a href="https://github.com/stabib08/liquid-trade/blob/main/docs/coinvest_capabilities.md">coinvest_capabilities.md</a>{" · "}
          <a href="https://github.com/stabib08/liquid-trade">source</a>
        </p>
        <p className="muted" style={{ fontSize: 12 }}>
          Not investment advice. Prices via yfinance (free, best-effort). Positioning via Co-Invest,
          handled truthfully and never fabricated. Point-in-time store with an enforced no-lookahead
          invariant; all analytics recomputable from an append-only, git-committed log.
        </p>
      </footer>
    </main>
  );
}
