import { API } from "../config";
import { useState, useEffect, useRef, useCallback } from "react";

const panel = {
  background: "var(--glass-card)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "28px",
};
const mono = { fontFamily: "var(--font-mono)" };

/* ── Circular score gauge ─────────────────────────────── */
function ScoreGauge({ score, label }) {
  const lc    = (label || "neutral").toLowerCase();
  const color = lc === "bullish" ? "var(--green)" : lc === "bearish" ? "var(--red)" : "var(--gold)";
  const r     = 54;
  const circ  = 2 * Math.PI * r;
  const fill  = circ * (1 - (score ?? 50) / 100);

  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ position: "relative", width: 140, height: 140, margin: "0 auto 16px" }}>
        <svg viewBox="0 0 140 140" style={{ position: "absolute", inset: 0, transform: "rotate(-90deg)" }}>
          <circle cx="70" cy="70" r={r} fill="none" stroke="var(--subtle)" strokeWidth="10" />
          <circle cx="70" cy="70" r={r} fill="none"
            stroke={color} strokeWidth="10"
            strokeDasharray={circ}
            strokeDashoffset={fill}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.4s" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ ...mono, fontSize: 30, fontWeight: 500, color }}>{score ?? 50}</span>
          <span style={{ ...mono, fontSize: 9, color: "var(--muted)", letterSpacing: 2 }}>/ 100</span>
        </div>
      </div>
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 8,
        padding: "5px 16px", borderRadius: 100,
        border: `1px solid ${color}33`, background: `${color}12`,
        ...mono, fontSize: 12, letterSpacing: 1, color,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />
        {label ?? "Neutral"}
      </div>
    </div>
  );
}

/* ── Feature bar ─────────────────────────────────────── */
function FeatureBar({ label, value, max = 10, color = "var(--gold)" }) {
  const pct = Math.min(100, max > 0 ? (value / max) * 100 : 0);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
        <span style={{ ...mono, fontSize: 11, color }}>{value}</span>
      </div>
      <div style={{ height: 3, background: "var(--subtle)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

/* ── Keyword chip ────────────────────────────────────── */
function Chip({ word, type }) {
  const s = {
    bull:    { bg: "var(--green-dim)", bdr: "rgba(74,222,128,0.25)",  c: "var(--green)" },
    bear:    { bg: "var(--red-dim)",   bdr: "rgba(248,113,113,0.25)", c: "var(--red)"   },
    neutral: { bg: "var(--gold-dim)",  bdr: "var(--border-gold)",     c: "var(--gold)"  },
  }[type] || { bg: "var(--glass)", bdr: "var(--border)", c: "var(--muted)" };

  return (
    <span style={{
      display: "inline-block",
      padding: "3px 10px", margin: "3px",
      borderRadius: 100,
      background: s.bg, border: `1px solid ${s.bdr}`,
      ...mono, fontSize: 11, color: s.c,
    }}>
      {word}
    </span>
  );
}

/* ── Investor use cases ──────────────────────────────── */
const USE_CASES = [
  {
    icon: "↗",
    title: "Contrarian Signal",
    desc: "When extreme bullish bias (80+) appears across multiple outlets on the same stock, the optimistic narrative is often already priced in. Your model gives a quantified way to measure consensus before it becomes a trap.",
  },
  {
    icon: "⇌",
    title: "Sentiment Divergence",
    desc: "The most valuable signal is conflicting bias across sources covering the same event. Reuters neutral, CNBC bullish, Seeking Alpha bearish — that divergence means the market hasn't formed consensus, and you can position before it does.",
  },
  {
    icon: "◎",
    title: "Earnings Anticipation",
    desc: "Track rolling sentiment 2–3 weeks before earnings. If score has been building extremely bullish, the stock is vulnerable to selling even on a good report — 'buy the rumor, sell the news' in quantified form.",
  },
  {
    icon: "⊘",
    title: "Personal Reading Filter",
    desc: "Every article gets a bias score before you engage with it, so you approach coverage with calibrated skepticism rather than absorbing framing unconsciously. This alone makes the tool worth building.",
  },
];

/* ── Bias dimensions ─────────────────────────────────── */
const DIMENSIONS = [
  {
    title: "Directional Bias",   difficulty: "Easiest · Live",
    desc: "Is the article pushing bullish or bearish framing beyond what facts support? Scored in real time via keyword engine with negation handling.",
    color: "var(--gold)",
  },
  {
    title: "Loaded Language",    difficulty: "Moderate · Live",
    desc: "Words like 'surged', 'collapsed', 'soared', 'plunged' carry emotional weight neutral reporting doesn't need. Engine flags and highlights every triggering word.",
    color: "var(--cyan)",
  },
  {
    title: "Framing Bias",       difficulty: "Hard · Planned",
    desc: "Which facts are chosen, which omitted, how ordered? Requires cross-source comparison — you can't detect omission from one article alone. Planned for multi-source pipeline.",
    color: "var(--red)",
  },
  {
    title: "Systemic Outlet Bias", difficulty: "Long-term · Planned",
    desc: "Does a publication consistently lean one direction? Requires longitudinal analysis across hundreds of articles. Planned as outlet-level bias profiles.",
    color: "var(--green)",
  },
];

/* ══════════════════════════════════════════════════════
   MAIN COMPONENT
══════════════════════════════════════════════════════ */
export default function Bias() {
  const [inputText, setInputText] = useState("");
  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [keywords,  setKeywords]  = useState(null);
  const [kwTab,     setKwTab]     = useState("bullish");
  const [kwCatTab,  setKwCatTab]  = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/bias/keywords`)
      .then(r => r.json())
      .then(d => {
        setKeywords(d);
        if (d?.bullish) setKwCatTab(Object.keys(d.bullish)[0]);
      })
      .catch(() => {});
  }, []);

  const runAnalysis = useCallback((text) => {
    if (!text.trim()) { setResult(null); return; }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res  = await fetch(`${API}/bias/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        setResult(await res.json());
      } catch {
        setResult(null);
      } finally {
        setLoading(false);
      }
    }, 600);
  }, []);

  const label = result?.label || "Neutral";
  const lc    = label.toLowerCase();
  const maxKw = Math.max((result?.bull_count ?? 0) + (result?.bear_count ?? 0), 1);

  return (
    <div className="bias-page">

      {/* ── Header ──────────────────────────────────────── */}
      <div className="section-header">
        <h1>Bias Score System</h1>
        <p>Live analysis engine · Keyword lexicon · Investor intelligence framework</p>
      </div>

      {/* ── Score range overview ─────────────────────────── */}
      <div className="bias-grid">
        <div className="bias-card bearish">
          <div className="bias-score-label">Score Range</div>
          <h2>0 – 40</h2>
          <h3>Bearish</h3>
          <p>Fear-driven headlines, downside risk framing, crisis language, pessimistic analyst calls. Potential contrarian opportunity at extremes.</p>
        </div>
        <div className="bias-card neutral">
          <div className="bias-score-label">Score Range</div>
          <h2>41 – 59</h2>
          <h3>Neutral</h3>
          <p>Balanced reporting with hedge language present. Multiple perspectives represented. Data-driven over narrative-driven journalism.</p>
        </div>
        <div className="bias-card bullish">
          <div className="bias-score-label">Score Range</div>
          <h2>60 – 100</h2>
          <h3>Bullish</h3>
          <p>Positive framing, optimistic projections, upgrade language, hype narratives. Watch for consensus traps when score exceeds 80.</p>
        </div>
      </div>

      {/* ── LIVE ANALYZER ─────────────────────────────────── */}
      <div style={{ padding: "0 48px 36px" }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 24, fontWeight: 400, marginBottom: 6 }}>
          Live Bias Analyzer
        </h3>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
          Paste any financial headline or paragraph. Scored in real time using keyword detection, negation window handling, and hedge dampening.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>

          {/* Input panel */}
          <div style={panel}>
            <div style={{ ...mono, fontSize: 9, letterSpacing: 2.5, color: "var(--muted)", textTransform: "uppercase", marginBottom: 12 }}>
              Input Text
            </div>
            <textarea
              value={inputText}
              onChange={e => { setInputText(e.target.value); runAnalysis(e.target.value); }}
              placeholder={"Paste a financial headline or paragraph…\n\nExample: Sensex surged to a record high today, beating analyst expectations as FII inflows accelerated amid strong global tailwinds."}
              rows={9}
              style={{
                width: "100%", resize: "vertical",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text)",
                fontFamily: "var(--font-ui)",
                fontSize: 14, lineHeight: 1.7,
                padding: "12px 14px", outline: "none",
                transition: "border-color 0.2s",
              }}
              onFocus={e => e.target.style.borderColor = "var(--border-gold)"}
              onBlur={e  => e.target.style.borderColor = "var(--border)"}
            />
            <div style={{ ...mono, fontSize: 10, color: "var(--muted)", marginTop: 8 }}>
              {inputText.length} chars · {inputText.trim().split(/\s+/).filter(Boolean).length} words
            </div>
          </div>

          {/* Result panel */}
          <div style={panel}>
            <div style={{ ...mono, fontSize: 9, letterSpacing: 2.5, color: "var(--muted)", textTransform: "uppercase", marginBottom: 16 }}>
              {loading ? "Analyzing…" : result ? "Analysis Result" : "Awaiting Input"}
            </div>

            {!result && !loading && (
              <p style={{ color: "var(--muted)", fontSize: 13, lineHeight: 1.75 }}>
                Start typing to see live bias analysis — keyword detection, negation handling, hedge dampening, and investor signal.
              </p>
            )}

            {loading && (
              <p style={{ ...mono, fontSize: 12, color: "var(--gold)", letterSpacing: 1 }}>Running keyword engine…</p>
            )}

            {result && !loading && (
              <>
                <ScoreGauge score={result.bias} label={result.label} />

                <div style={{ marginTop: 24 }}>
                  <FeatureBar label="Bullish keywords" value={result.bull_count ?? 0} max={maxKw} color="var(--green)" />
                  <FeatureBar label="Bearish keywords" value={result.bear_count ?? 0} max={maxKw} color="var(--red)" />
                  <FeatureBar label="Hedge / neutral"  value={result.hedge_count ?? 0} max={10}   color="var(--muted)" />
                  <FeatureBar label="Negation flips"   value={(result.negated_bull ?? 0) + (result.negated_bear ?? 0)} max={5} color="var(--cyan)" />
                </div>

                {(result.bull_hits?.length > 0 || result.bear_hits?.length > 0) && (
                  <div style={{ marginTop: 20 }}>
                    <div style={{ ...mono, fontSize: 9, letterSpacing: 2, color: "var(--muted)", textTransform: "uppercase", marginBottom: 8 }}>
                      Triggered Keywords
                    </div>
                    {result.bull_hits?.map(w => <Chip key={w} word={w} type="bull" />)}
                    {result.bear_hits?.map(w => <Chip key={w} word={w} type="bear" />)}
                  </div>
                )}

                {result.investor_signal && (
                  <div style={{
                    marginTop: 20,
                    borderLeft: "2px solid var(--gold)",
                    paddingLeft: 12,
                    fontSize: 12, lineHeight: 1.75,
                    color: "var(--gold)", opacity: 0.85,
                  }}>
                    {result.investor_signal}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── KEYWORD LEXICON ────────────────────────────────── */}
      <div style={{ padding: "0 48px 36px" }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 24, fontWeight: 400, marginBottom: 6 }}>
          Keyword Lexicon
        </h3>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
          Complete vocabulary used by the scoring engine, structured from Loughran-McDonald Financial Sentiment methodology with Indian market extensions.
        </p>

        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {["bullish", "bearish", "hedge"].map(t => {
            const col = t === "bullish" ? "var(--green)" : t === "bearish" ? "var(--red)" : "var(--gold)";
            const act = kwTab === t;
            return (
              <button key={t} onClick={() => {
                setKwTab(t);
                if (t !== "hedge" && keywords?.[t]) setKwCatTab(Object.keys(keywords[t])[0]);
              }} style={{
                padding: "7px 22px", borderRadius: 100,
                border: `1px solid ${act ? col : "var(--border)"}`,
                background: act ? `${col}15` : "var(--glass)",
                backdropFilter: "blur(12px)",
                color: act ? col : "var(--muted)",
                fontFamily: "var(--font-ui)", fontSize: 12, fontWeight: 700,
                letterSpacing: 1, textTransform: "uppercase", cursor: "pointer",
                transition: "all 0.2s",
              }}>
                {t}
              </button>
            );
          })}
        </div>

        <div style={panel}>
          {!keywords && (
            <p style={{ ...mono, fontSize: 13, color: "var(--muted)" }}>Connecting to keyword engine…</p>
          )}

          {keywords && kwTab === "hedge" && (
            <>
              <div style={{ ...mono, fontSize: 9, letterSpacing: 2, color: "var(--muted)", textTransform: "uppercase", marginBottom: 12 }}>
                Hedge & Neutral Language — pulls directional score toward 50
              </div>
              {keywords.hedge?.map(w => <Chip key={w} word={w} type="neutral" />)}
            </>
          )}

          {keywords && kwTab !== "hedge" && (
            <>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
                {Object.keys(keywords[kwTab] || {}).map(cat => (
                  <button key={cat} onClick={() => setKwCatTab(cat)} style={{
                    padding: "4px 14px", borderRadius: 6,
                    border: `1px solid ${kwCatTab === cat ? "var(--border-gold)" : "var(--border)"}`,
                    background: kwCatTab === cat ? "var(--gold-dim)" : "none",
                    color: kwCatTab === cat ? "var(--gold)" : "var(--muted)",
                    ...mono, fontSize: 10, cursor: "pointer",
                  }}>
                    {cat}
                  </button>
                ))}
              </div>
              {(keywords[kwTab]?.[kwCatTab] || []).map(w => (
                <Chip key={w} word={w} type={kwTab === "bullish" ? "bull" : "bear"} />
              ))}
            </>
          )}
        </div>
      </div>

      {/* ── 4 BIAS DIMENSIONS ─────────────────────────────── */}
      <div style={{ padding: "0 48px 36px" }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 24, fontWeight: 400, marginBottom: 6 }}>
          Four Dimensions of Financial Bias
        </h3>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
          Bias operates on multiple axes. ArthraAI currently scores Dimensions 1 & 2 live. Dimensions 3 & 4 require cross-source comparison — planned for future releases.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 16 }}>
          {DIMENSIONS.map(({ title, difficulty, desc, color }) => (
            <div key={title} style={{ ...panel, borderLeft: `3px solid ${color}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <span style={{ fontFamily: "var(--font-display)", fontSize: 18 }}>{title}</span>
                <span style={{ ...mono, fontSize: 9, color: "var(--muted)", letterSpacing: 1.5, paddingTop: 3 }}>{difficulty}</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.75, color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── INVESTOR USE CASES ────────────────────────────── */}
      <div style={{ padding: "0 48px 36px" }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 24, fontWeight: 400, marginBottom: 6 }}>
          Using Bias Detection to Your Advantage
        </h3>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
          The real advantage isn't predicting the future — it's knowing what narrative the market has already priced in. Prices move on surprises relative to expectations.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 16 }}>
          {USE_CASES.map(({ icon, title, desc }) => (
            <div key={title} style={panel}>
              <div style={{ fontSize: 24, marginBottom: 10, color: "var(--gold)" }}>{icon}</div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 8 }}>{title}</div>
              <p style={{ fontSize: 13, lineHeight: 1.75, color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── HOW IT'S CALCULATED ───────────────────────────── */}
      <div className="bias-howit">
        <h3>How the Score is Calculated</h3>
        <div className="bias-steps">
          {[
            { num: "01", title: "Keyword Counting",
              desc: "Bullish and bearish keywords are detected across 5 categories each (Price Movement, Growth, Optimism/Pessimism, Analyst Language, and Crisis/Confidence language). Multi-word phrases matched as token sequences." },
            { num: "02", title: "Negation Window (4-token lookback)",
              desc: "Before each keyword, a 4-token window checks for negation terms ('not', 'failed to', 'did not', etc.). A negated bullish keyword becomes a bearish signal and vice versa — the key fix that pure keyword matching misses." },
            { num: "03", title: "Hedge Dampening",
              desc: "Hedge words ('may', 'could', 'uncertain', 'however') proportionally pull the raw score toward 50, reflecting balanced reporting. Maximum 50% dampening. This is why 'could surge' scores more neutrally than 'surged'." },
          ].map(({ num, title, desc }) => (
            <div key={num} className="bias-step">
              <div className="step-num">STEP {num}</div>
              <div className="step-title">{title}</div>
              <p className="step-desc">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── DISCLAIMER ────────────────────────────────────── */}
      <div className="bias-disclaimer">
        <h3>Disclaimer</h3>
        <p>
          ArthraAI bias scores are computed by a keyword engine informed by the Loughran-McDonald
          Financial Sentiment Dictionary methodology and extended for Indian markets. Scores reflect
          detectable framing and tone patterns — not market direction or investment advice.
          The bias detector identifies how a story is written, not whether the facts are correct.
          Always cross-reference with primary sources before making investment decisions.
        </p>
      </div>
    </div>
  );
}