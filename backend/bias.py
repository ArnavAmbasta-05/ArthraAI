"""
bias.py — Full 4-dimension bias analysis for ArthraAI
Based on Bias_Finance.txt framework:
  Dim 1: Directional bias (keyword score)
  Dim 2: Loaded language (which words triggered)
  Dim 3: Hedge ratio (balance signal)
  Dim 4: Negation complexity (flipped signals)
"""

from ai import score_bias, generate


def analyze_bias(text: str) -> dict:
    if not text or not text.strip():
        return {
            "bias": 50, "label": "Neutral", "summary": "", "insight": "",
            "loaded_language_flags": [], "hedge_ratio": 0.0,
            "negation_flips": 0, "bias_dimensions": {}, "investor_signal": "",
            "bull_hits": [], "bear_hits": [], "bull_count": 0, "bear_count": 0,
            "hedge_count": 0, "negated_bull": 0, "negated_bear": 0,
        }

    kw = score_bias(text)

    # Dim 1
    directional_score = kw["score"]

    # Dim 2
    loaded_words   = list(set(kw["bull_hits"] + kw["bear_hits"]))
    loaded_intensity = min(100, len(loaded_words) * 12)

    # Dim 3
    total_signals = kw["bull_count"] + kw["bear_count"] + kw["hedge_count"]
    hedge_ratio   = round(kw["hedge_count"] / max(total_signals, 1), 2)
    balance_score = round(hedge_ratio * 100)

    # Dim 4
    negation_flips        = kw["negated_bull"] + kw["negated_bear"]
    negation_complexity   = min(100, negation_flips * 25)

    bias_dimensions = {
        "directional":         directional_score,
        "loaded_lang":         loaded_intensity,
        "balance":             balance_score,
        "negation_complexity": negation_complexity,
    }

    # Investor signal (from document use cases)
    label = kw["label"]
    if directional_score >= 80:
        investor_signal = (
            "Extreme bullish consensus. Per contrarian analysis, this level of "
            "optimism may already be priced in — watch for disappointment risk "
            "if facts diverge from narrative."
        )
    elif directional_score >= 60:
        investor_signal = (
            "Bullish framing detected. Approach with calibrated optimism; "
            "verify underlying data matches the positive tone before acting."
        )
    elif directional_score <= 20:
        investor_signal = (
            "Extreme bearish framing. Fear-driven language may exaggerate downside. "
            "Check whether facts support the severity of tone before acting on this coverage."
        )
    elif directional_score <= 40:
        investor_signal = (
            "Bearish framing detected. Some downside risk signaled. "
            "Cross-reference with neutral wire sources before drawing conclusions."
        )
    else:
        investor_signal = (
            "Neutral or balanced coverage. "
            "Hedge language present — multiple perspectives likely represented."
        )

    # Summary via flan-t5
    prompt  = (
        f"Summarize this {label.lower()} financial article neutrally in 1-2 sentences. "
        f"Article: {text[:600]}"
    )
    raw     = generate(prompt)
    summary = raw[:200] if raw else text[:150]

    return {
        "bias":                  directional_score,
        "label":                 label,
        "summary":               summary,
        "insight":               investor_signal,
        "loaded_language_flags": loaded_words,
        "hedge_ratio":           hedge_ratio,
        "negation_flips":        negation_flips,
        "bias_dimensions":       bias_dimensions,
        "investor_signal":       investor_signal,
        "bull_hits":             kw["bull_hits"],
        "bear_hits":             kw["bear_hits"],
        "bull_count":            kw["bull_count"],
        "bear_count":            kw["bear_count"],
        "hedge_count":           kw["hedge_count"],
        "negated_bull":          kw["negated_bull"],
        "negated_bear":          kw["negated_bear"],
    }