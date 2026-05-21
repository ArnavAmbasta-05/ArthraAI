import os, re, json, torch
from pathlib import Path

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"]       = "1"

BASE_DIR     = Path(__file__).resolve().parent.parent
FINBERT_PATH = BASE_DIR / "local-model" / "finbert"
FLANL_PATH   = BASE_DIR / "local-model" / "flan-t5"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"⚡ ArthraAI AI engine | device: {device}")

# ── Load FinBERT ───────────────────────────────────────────
_finbert_tok = _finbert_model = None
if FINBERT_PATH.exists():
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        print(f"🔍 Loading FinBERT from {FINBERT_PATH}")
        _finbert_tok   = AutoTokenizer.from_pretrained(str(FINBERT_PATH), local_files_only=True)
        _finbert_model = AutoModelForSequenceClassification.from_pretrained(
            str(FINBERT_PATH), local_files_only=True
        ).to(device).eval()
        print("✅ FinBERT loaded")
    except Exception as e:
        print(f"⚠️  FinBERT load failed: {e} — keyword-only fallback active")
else:
    print(f"⚠️  FinBERT not found at {FINBERT_PATH}")
    print("   Run: python download_model.py && python train_model.py")

# ── Load flan-t5-base ──────────────────────────────────────
_flan_tok = _flan_model = None
if FLANL_PATH.exists():
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        print(f"🔍 Loading flan-t5 from {FLANL_PATH}")
        _flan_tok   = AutoTokenizer.from_pretrained(str(FLANL_PATH), local_files_only=True)
        _flan_model = AutoModelForSeq2SeqLM.from_pretrained(
            str(FLANL_PATH), local_files_only=True
        ).to(device).eval()
        print("✅ flan-t5-base loaded")
    except Exception as e:
        print(f"⚠️  flan-t5 load failed: {e} — text fallback active")
else:
    print(f"⚠️  flan-t5 not found at {FLANL_PATH}")
    print("   Run: python download_model.py && python train_model.py")


# ══════════════════════════════════════════════════════════
# KEYWORD LEXICON  (Layer 1)
# Five categories per direction — Indian market extended.
# ══════════════════════════════════════════════════════════

_BULL_PRICE = {
    "surged","soared","skyrocketed","rallied","climbed","jumped","spiked",
    "rebounded","recovered","gained","rose","lifted","surges","soars",
    "rallies","climbs","jumps","rebounds","recovers","scaled","hit record",
}
_BULL_GROWTH = {
    "record high","all-time high","outperformed","beat expectations","exceeded",
    "robust","accelerated","expanded","booming","thriving","momentum",
    "breakout","multi-year high","best ever","highest ever",
}
_BULL_OPTIMISM = {
    "promising","optimistic","bullish","upside potential","buy opportunity",
    "undervalued","growth trajectory","positive outlook","bright future",
    "tailwinds","attractive valuation","strong pipeline",
}
_BULL_ANALYST = {
    "upgrade","overweight","buy rating","price target raised","strong buy",
    "accumulate","conviction buy","outperform","raised target",
    "upped target","initiate buy","top pick",
}
_BULL_INDIA = {
    "fii inflows","dii buying","record sip","gst surplus","fiscal surplus",
    "rate cut","rbi accommodative","capex boost","pli scheme",
    "rupee strengthened","india gdp raised",
}

BULLISH_WORDS: set[str] = (
    _BULL_PRICE | _BULL_GROWTH | _BULL_OPTIMISM | _BULL_ANALYST | _BULL_INDIA
)

_BEAR_PRICE = {
    "plunged","collapsed","tanked","cratered","slumped","tumbled","fell",
    "dropped","sank","declined","erased","wiped out","nosedived",
    "plunges","craters","slumps","tumbles","drops","crashed","crashing",
}
_BEAR_WEAKNESS = {
    "missed expectations","disappointing","weak","concerning","deteriorating",
    "shrinking","contracting","struggling","underperforming","headwinds",
    "below expectations","weaker than expected","shortfall","deficit",
    "profit warning","guidance cut","revenue miss",
}
_BEAR_PESSIMISM = {
    "bearish","overvalued","downside risk","sell signal","caution",
    "warning signs","red flags","bleak","troubled","vulnerable",
    "selloff","sell-off","correction","risk-off","flight to safety",
}
_BEAR_ANALYST = {
    "downgrade","underweight","sell rating","price target cut","avoid",
    "reduce","exit","cut target","lowered target","downgraded",
    "cut its rating","initiate sell","bear case",
}
_BEAR_INDIA = {
    "fii outflows","npa rising","rbi concern","fiscal slippage",
    "rupee weakened","inflation breach","rate hike","credit crunch",
    "liquidity squeeze","margin call","circuit breaker",
}

BEARISH_WORDS: set[str] = (
    _BEAR_PRICE | _BEAR_WEAKNESS | _BEAR_PESSIMISM | _BEAR_ANALYST | _BEAR_INDIA
)

HEDGE_WORDS: set[str] = {
    "may","might","could","possibly","potentially","some analysts",
    "according to","remains to be seen","mixed signals","volatile",
    "uncertain","however","despite","but","although","while","though",
    "nevertheless","yet","even so","that said","too early","unclear",
    "analysts differ","mixed","cautious","wait and watch","divided opinion",
}

NEGATION_TERMS: set[str] = {
    "not","no","never","didn't","did not","won't","will not",
    "hasn't","has not","haven't","have not","wasn't","was not",
    "weren't","were not","isn't","is not","aren't","are not",
    "failed to","unable to","refused to","stopped","halted",
}

KEYWORD_CATEGORIES = {
    "bullish": {
        "Price Movement":    sorted(_BULL_PRICE),
        "Growth & Strength": sorted(_BULL_GROWTH),
        "Forward Optimism":  sorted(_BULL_OPTIMISM),
        "Analyst Language":  sorted(_BULL_ANALYST),
        "India-Specific":    sorted(_BULL_INDIA),
    },
    "bearish": {
        "Price Movement":    sorted(_BEAR_PRICE),
        "Weakness & Risk":   sorted(_BEAR_WEAKNESS),
        "Forward Pessimism": sorted(_BEAR_PESSIMISM),
        "Analyst Language":  sorted(_BEAR_ANALYST),
        "India-Specific":    sorted(_BEAR_INDIA),
    },
    "hedge": sorted(HEDGE_WORDS),
}


# ══════════════════════════════════════════════════════════
# LAYER 1 — KEYWORD SCORING
# ══════════════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _has_negation(tokens: list[str], pos: int, window: int = 4) -> bool:
    start = max(0, pos - window)
    for neg in NEGATION_TERMS:
        nw = neg.split()
        for i in range(start, pos):
            if tokens[i:i+len(nw)] == nw:
                return True
    return False


def score_bias(text: str) -> dict:
    tokens = _tokenize(text)
    if not tokens:
        return {"score": 50, "label": "Neutral", "bull_hits": [], "bear_hits": [],
                "hedge_count": 0, "negated_bull": 0, "negated_bear": 0,
                "bull_count": 0, "bear_count": 0}

    bull_hits, bear_hits = [], []
    negated_bull = negated_bear = hedge_count = 0

    for w in HEDGE_WORDS:
        wt = w.split()
        for i in range(len(tokens) - len(wt) + 1):
            if tokens[i:i+len(wt)] == wt:
                hedge_count += 1

    for phrase in BULLISH_WORDS:
        pt = phrase.split()
        for i in range(len(tokens) - len(pt) + 1):
            if tokens[i:i+len(pt)] == pt:
                (negated_bull := negated_bull + 1) if _has_negation(tokens, i) else bull_hits.append(phrase)

    for phrase in BEARISH_WORDS:
        pt = phrase.split()
        for i in range(len(tokens) - len(pt) + 1):
            if tokens[i:i+len(pt)] == pt:
                (negated_bear := negated_bear + 1) if _has_negation(tokens, i) else bear_hits.append(phrase)

    bull_count = len(bull_hits) + negated_bear
    bear_count = len(bear_hits) + negated_bull
    total      = bull_count + bear_count
    raw        = (bull_count / total * 100) if total > 0 else 50.0
    hedge_r    = min(hedge_count / max(total, 1), 0.5)
    score      = max(0, min(100, round(raw + (50 - raw) * hedge_r)))
    label      = "Bearish" if score < 40 else "Bullish" if score > 60 else "Neutral"

    return {"score": score, "label": label, "bull_hits": list(set(bull_hits)),
            "bear_hits": list(set(bear_hits)), "hedge_count": hedge_count,
            "negated_bull": negated_bull, "negated_bear": negated_bear,
            "bull_count": bull_count, "bear_count": bear_count}


# ══════════════════════════════════════════════════════════
# LAYER 2 — FINBERT CLASSIFICATION SCORE
# FinBERT label order: NEGATIVE(0)=Bearish, NEUTRAL(1)=Neutral, POSITIVE(2)=Bullish
# Score = prob[0]*0 + prob[1]*50 + prob[2]*100
# ══════════════════════════════════════════════════════════

def _finbert_score(text: str) -> float | None:
    if _finbert_model is None:
        return None
    try:
        enc = _finbert_tok(text, truncation=True, max_length=128,
                           return_tensors="pt").to(device)
        with torch.no_grad():
            logits = _finbert_model(**enc).logits[0].cpu().float()
        probs = torch.softmax(logits, dim=-1).numpy()
        return round(float(probs[0] * 0 + probs[1] * 50 + probs[2] * 100), 2)
    except Exception as e:
        print(f"⚠️  FinBERT inference: {e}")
        return None


# ══════════════════════════════════════════════════════════
# LAYER 3 — FLAN-T5-BASE TEXT GENERATION
# ══════════════════════════════════════════════════════════

def _generate_text(text: str, label: str) -> dict:
    if _flan_model is None:
        return {"summary": text[:200].strip(), "insight": ""}
    try:
        def _run(prompt: str, max_new: int) -> str:
            enc = _flan_tok(prompt, return_tensors="pt",
                            truncation=True, max_length=256).to(device)
            with torch.no_grad():
                out = _flan_model.generate(
                    **enc, max_new_tokens=max_new, num_beams=4,
                    no_repeat_ngram_size=2, early_stopping=True,
                )
            return _flan_tok.decode(out[0], skip_special_tokens=True).strip()

        summary = _run(f"summarize financial news: {text[:500]}", 100)
        insight = _run(
            f"one-line investor insight for {label.lower()} financial news: {text[:300]}", 60
        )
        return {"summary": summary or text[:200], "insight": insight}
    except Exception as e:
        print(f"⚠️  flan-t5 generation: {e}")
        return {"summary": text[:200], "insight": ""}


# ══════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════

_DEFAULT = {"bias": 50, "label": "Neutral", "summary": "", "insight": ""}


def process_news(text: str) -> dict:
    if not text or not text.strip():
        return _DEFAULT.copy()

    kw            = score_bias(text)
    kw_score      = kw["score"]
    finbert_score = _finbert_score(text)

    if finbert_score is not None:
        hybrid = round(0.60 * finbert_score + 0.40 * kw_score)
    else:
        hybrid = kw_score

    hybrid = max(0, min(100, hybrid))
    label  = "Bearish" if hybrid < 40 else "Bullish" if hybrid > 60 else "Neutral"
    tf     = _generate_text(text, label)

    return {
        "bias":          hybrid,
        "label":         label,
        "summary":       tf["summary"],
        "insight":       tf["insight"],
        "bull_hits":     kw["bull_hits"],
        "bear_hits":     kw["bear_hits"],
        "hedge_count":   kw["hedge_count"],
        "bull_count":    kw["bull_count"],
        "bear_count":    kw["bear_count"],
        "negated_bull":  kw["negated_bull"],
        "negated_bear":  kw["negated_bear"],
        "finbert_score": finbert_score,
        "kw_score":      kw_score,
    }


def generate(prompt: str) -> str | None:
    """Legacy: arbitrary flan-t5 generation for bias.py."""
    if _flan_model is None:
        return None
    try:
        enc = _flan_tok(prompt, return_tensors="pt",
                        truncation=True, max_length=256).to(device)
        with torch.no_grad():
            out = _flan_model.generate(
                **enc, max_new_tokens=180, num_beams=4,
                no_repeat_ngram_size=2, early_stopping=True,
            )
        return _flan_tok.decode(out[0], skip_special_tokens=True)
    except Exception as e:
        print(f"⚠️  generate(): {e}")
        return None


def safe_parse(text: str | None) -> dict:
    return _DEFAULT.copy()