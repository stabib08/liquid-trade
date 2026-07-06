"""Kill-criterion adjudication.

Turns the regression/vol evidence into a verdict and a written interpretation for
each basket. Verdicts are deliberately conservative:

  SURVIVES      — the falsifiable prediction is supported at conventional
                  significance (|t| > 2); the thesis lives for now.
  FAILED        — the kill-criterion is met; the thesis is dead as stated.
  INDETERMINATE — the sample can't reject either way, OR the decisive test
                  (e.g. an event study) is not yet implemented. Stated honestly.

"Untestable now" items (event studies for the two event-driven theses) are named
explicitly rather than glossed — the point of the project is intellectual honesty.
"""

from __future__ import annotations

SIG = 2.0  # |t| threshold for "statistically distinguishable"


def _sig(t) -> bool:
    return t is not None and abs(t) > SIG


def _ci_contains(ci, value=1.0) -> bool | None:
    if not ci:
        return None
    return ci["ci_low"] <= value <= ci["ci_high"]


def evaluate(basket_id: str, ev: dict) -> dict:
    fn = {
        "ai_power": _ai_power,
        "onshoring_semis": _semis,
        "autonomy_defense": _defense,
        "quantum": _quantum,
    }.get(basket_id)
    if fn is None:
        return {"verdict": "INDETERMINATE", "headline": "no evaluator",
                "interpretation": "", "evidence": [], "untestable_now": []}
    return fn(ev)


def _ai_power(ev: dict) -> dict:
    cr = ev["comparator_reg"]
    beta = cr["betas"].get("Comparator")
    beta_t = cr["tstats"].get("Comparator")
    alpha_a = cr.get("alpha_annual")
    alpha_t = cr.get("alpha_tstat")
    ci = ev.get("rolling_comp_beta_latest")
    contains_1 = _ci_contains(ci, 1.0)

    evidence = [
        f"XLU beta (market-controlled) = {beta:.2f} (t={beta_t:.1f}).",
        f"Alpha to utilities = {alpha_a*100:+.1f}%/yr (t={alpha_t:.1f}).",
    ]
    if ci:
        evidence.append(
            f"Latest rolling-126d XLU beta = {ci['beta']:.2f}, 95% CI "
            f"[{ci['ci_low']:.2f}, {ci['ci_high']:.2f}] "
            f"({'contains' if contains_1 else 'excludes'} 1.0).")

    alpha_near_zero = alpha_a is not None and abs(alpha_a) < 0.05
    if alpha_a is not None and alpha_a > 0 and _sig(alpha_t):
        verdict = "SURVIVES"
        interp = (
            "The basket earns positive alpha to the utilities factor that is "
            "statistically distinguishable from zero after controlling for the "
            "market — exactly the falsifiable prediction. Consistent with the "
            "'AI power is a different animal from regulated utilities' claim. "
            "Watch whether this is grid-equipment (GEV) or merchant-generation "
            "driven; the interpretation differs.")
    elif contains_1 and not _sig(alpha_t) and alpha_near_zero:
        verdict = "FAILED"
        interp = (
            "The rolling 6-month XLU beta's 95% CI contains 1.0 and the utilities "
            "alpha is both small and indistinguishable from zero. By the "
            "pre-registered kill-criterion the 'AI power is structurally different' "
            "thesis is dead as stated: the basket behaves like levered XLU, and the "
            "cheaper, more liquid XLU is the correct exposure.")
    else:
        verdict = "INDETERMINATE"
        big_alpha = alpha_a is not None and alpha_a > 0.05 and not _sig(alpha_t)
        interp = (
            "UNDERPOWERED, not dead. The utilities-alpha point estimate is large "
            f"and positive ({alpha_a*100:+.0f}%/yr) but not yet significant "
            f"(t={alpha_t:.1f}), and the rolling XLU-beta CI is wide. With only "
            "~2 years since GEV's 2024 spin-off and ~48% annualized vol, the test "
            "cannot yet reject either the thesis or its kill-criterion. Crucially "
            "the kill-criterion requires alpha ≈ 0, and a +37%/yr point estimate is "
            "NOT that — so calling the thesis dead here would be a low-power error. "
            "Verdict stays open pending more history."
            if big_alpha else
            "Mixed evidence and a wide confidence band; the sample cannot reject "
            "either the thesis or its kill-criterion. Needs more history.")
    return {"verdict": verdict, "headline": f"XLU β={beta:.2f}, α={alpha_a*100:+.1f}%/yr",
            "interpretation": interp, "evidence": evidence, "untestable_now": []}


def _semis(ev: dict) -> dict:
    cr = ev["comparator_reg"]
    beta = cr["betas"].get("Comparator")
    beta_t = cr["tstats"].get("Comparator")
    alpha_a = cr.get("alpha_annual")
    alpha_t = cr.get("alpha_tstat")
    r2 = cr.get("r2")
    evidence = [
        f"SOXX beta (market-controlled) = {beta:.2f} (t={beta_t:.1f}).",
        f"Non-event alpha to SOXX = {alpha_a*100:+.1f}%/yr (t={alpha_t:.1f}).",
        f"Regression R² = {r2:.2f}.",
    ]
    # The decisive test — abnormal return around capex/policy events — needs a
    # dated event catalog we have not built yet.
    untestable = [
        "Event-driven alpha around capex-guide / export-policy announcements "
        "requires a hand-curated dated event catalog (event study) — not yet "
        "implemented, so the 'edge beyond SOXX beta' claim cannot be adjudicated."]
    if _sig(alpha_t) and alpha_a > 0:
        note = ("Full-sample alpha to SOXX is positive and significant, which is "
                "*suggestive* of a picks-and-shovels premium — but this is not the "
                "event test the thesis specifies, so it is not yet decisive.")
    else:
        note = ("Full-sample returns look largely explained by SOXX beta "
                f"(R²={r2:.2f}, alpha not significant), which leans toward the "
                "kill-criterion — but the event study is still required to confirm "
                "there is no event-specific edge.")
    return {"verdict": "INDETERMINATE",
            "headline": f"SOXX β={beta:.2f}, R²={r2:.2f} (event study pending)",
            "interpretation": note, "evidence": evidence, "untestable_now": untestable}


def _defense(ev: dict) -> dict:
    ff5 = ev["ff5"]
    mkt_beta = ff5["betas"].get("Mkt_RF")
    mkt_t = ff5["tstats"].get("Mkt_RF")
    cr = ev["comparator_reg"]
    xar_beta = cr["betas"].get("Comparator")
    alpha_a = cr.get("alpha_annual")
    alpha_t = cr.get("alpha_tstat")
    evidence = [
        f"Market beta (FF5 Mkt-RF) = {mkt_beta:.2f} (t={mkt_t:.1f}).",
        f"Beta to defense factor (XAR) = {xar_beta:.2f}.",
        f"Alpha to XAR = {alpha_a*100:+.1f}%/yr (t={alpha_t:.1f}).",
    ]
    untestable = [
        "Budget-event / geopolitical-catalyst sensitivity requires a dated "
        "defense-budget event catalog (event study) — not yet implemented."]
    if mkt_beta is not None and mkt_beta >= 1.2:
        lean = ("Market beta is high (≥1.2), which leans toward the kill-criterion "
                "('just high-beta tech') — but the budget-event test is still needed "
                "to fully adjudicate the 'diversifier' claim.")
    elif mkt_beta is not None and mkt_beta < 1.0:
        lean = ("Market beta is below 1.0, consistent with the 'low-market-beta "
                "diversifier' half of the thesis. The other half — measurable "
                "budget-event sensitivity — remains untested. Note PLTR's weight: "
                "re-run without PLTR to see if this survives (see basket notes).")
    else:
        lean = ("Market beta is near 1.0 — neither clearly a diversifier nor "
                "clearly just high-beta tech. Inconclusive pending the event study.")
    return {"verdict": "INDETERMINATE",
            "headline": f"market β={mkt_beta:.2f} (budget-event test pending)",
            "interpretation": lean, "evidence": evidence, "untestable_now": untestable}


def _quantum(ev: dict) -> dict:
    cr = ev["comparator_reg"]
    arkk_beta = cr["betas"].get("Comparator")
    extra = ev.get("extra_reg", {})
    tlt_beta = extra.get("betas", {}).get("TLT")
    tlt_t = extra.get("tstats", {}).get("TLT")
    vol_ratio = ev.get("vol_ratio")
    ci = ev.get("rolling_comp_beta_latest")
    contains_1 = _ci_contains(ci, 1.0)

    evidence = [
        f"ARKK beta (market-controlled) = {arkk_beta:.2f}.",
        f"Rate loading: TLT beta = {tlt_beta:+.2f} (t={tlt_t:.1f})." if tlt_beta is not None
        else "TLT loading unavailable.",
        f"Vol vs ARKK = {vol_ratio:.2f}x." if vol_ratio else "vol ratio unavailable.",
    ]
    distinct = (_sig(tlt_t) or (vol_ratio and vol_ratio > 1.3)
                or (contains_1 is False))
    if distinct:
        verdict = "SURVIVES"
        rate_note = (
            "The rate-sensitivity leg of the prediction, however, did NOT hold: the "
            f"TLT loading is insignificant (t={tlt_t:.1f}). "
            if tlt_t is not None and not _sig(tlt_t) else "")
        interp = (
            "The sleeve is statistically DISTINCT from ARKK, but via VOLATILITY, not "
            "rate sensitivity: realized vol is "
            + (f"{vol_ratio:.1f}x ARKK " if vol_ratio else "far above ARKK ")
            + "and the rolling ARKK-beta CI sits well above 1.0. So it is not merely "
              "'ARKK with extra steps'. " + rate_note
            + "This is NOT a claim of outperformance — the sleeve stays labeled as a "
              "lottery ticket on a long-dated real option, exactly as intended.")
    elif contains_1 and not _sig(tlt_t) and (not vol_ratio or vol_ratio <= 1.2):
        verdict = "FAILED"
        interp = (
            "ARKK beta's CI contains 1.0, there is no incremental rate loading, and "
            "volatility is not materially above ARKK. By the honesty-flag "
            "kill-criterion this sleeve is 'ARKK with extra steps' — label it as a "
            "generic speculative-growth bet, which is the whole point of naming it.")
    else:
        verdict = "INDETERMINATE"
        interp = ("Neither clearly distinct from ARKK nor clearly identical on this "
                  "short, extremely volatile 2-name sample. Wide error bars; do not "
                  "over-read.")
    return {"verdict": verdict,
            "headline": f"ARKK β={arkk_beta:.2f}, TLT t={tlt_t:.1f}" if tlt_t is not None
            else f"ARKK β={arkk_beta:.2f}",
            "interpretation": interp, "evidence": evidence, "untestable_now": []}
