// Types mirroring src/report/out/report.json (produced by src/report/build.py).

export interface Stats {
  n_obs: number;
  start?: string;
  end?: string;
  cumulative_return?: number;
  annualized_return?: number;
  annualized_vol?: number;
  sharpe?: number;
  sortino?: number;
  max_drawdown?: number;
}

export interface Regression {
  n_obs: number;
  start?: string;
  end?: string;
  alpha_daily?: number;
  alpha_annual?: number;
  alpha_tstat?: number;
  betas?: Record<string, number>;
  tstats?: Record<string, number>;
  r2?: number;
  r2_adj?: number;
  hac_lags?: number;
  insufficient?: boolean;
}

export interface Verdict {
  verdict: "SURVIVES" | "FAILED" | "INDETERMINATE";
  headline: string;
  interpretation: string;
  evidence: string[];
  untestable_now: string[];
}

export interface Series {
  dates: string[];
  [k: string]: string[] | number[];
}

export interface Basket {
  id: string;
  name: string;
  speculative: boolean;
  thesis: string;
  falsifiable_prediction: string;
  kill_criterion: string;
  constituents: string[];
  primary_benchmark: string;
  natural_comparator: string;
  weighting_scheme: string;
  effective_n: number;
  verdict: Verdict;
  performance: {
    basket: Stats;
    benchmark: Stats;
    comparator: Stats;
    vol_ratio_vs_comparator: number | null;
  };
  factors: {
    ff5: Regression;
    thematic: Regression;
    comparator: Regression;
    rolling_comparator_beta_latest: { beta: number; ci_low: number; ci_high: number } | null;
  };
  equity_curves: { dates: string[]; basket: number[]; benchmark: number[]; comparator: number[] };
  rolling_sharpe: { dates: string[]; values: number[] };
  rolling_beta_series: { dates: string[]; beta: number[]; ci_low: number[]; ci_high: number[] } | null;
  rolling_corr: { dates: string[]; vs_SPY: number[]; vs_QQQ: number[] };
}

export interface Report {
  meta: {
    generated_at: string;
    code_version: string | null;
    python_version: string;
    price_source: string;
    factor_source: string;
    return_frequency: string;
    weighting: string;
    regression_se: string;
    rolling_beta_window_days: number;
    price_dates: [string, string];
    factor_dates: [string, string];
    n_ingest_runs: number | null;
    last_ingest: string | null;
    assumptions_note: string;
  };
  baskets: Basket[];
  cross_basket_correlation: {
    labels: string[];
    matrix: number[][];
    window: [string, string] | null;
  };
  positioning_overlay: {
    analyze_market: Record<string, {
      retail_long_frac: number | null;
      whale_long_frac: number | null;
      smart_money_divergence: number | null;
      mark_px: number | null;
      open_interest_usd: number | null;
      position_count: number | null;
      as_of: string;
    }>;
    pulse: { symbol: string; notional_usd: number }[];
  };
}
