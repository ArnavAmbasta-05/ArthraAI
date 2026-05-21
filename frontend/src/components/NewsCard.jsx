import { useState, useEffect, useCallback, useRef } from "react";

/* ─── localStorage read tracking ────────────────────── */
function getReadSet() {
  try { return new Set(JSON.parse(localStorage.getItem("arthra_read") || "[]")); }
  catch { return new Set(); }
}
function markRead(url) {
  try {
    const s = getReadSet(); s.add(url);
    localStorage.setItem("arthra_read", JSON.stringify([...s].slice(-500)));
  } catch {}
}

/* ─── Time formatter ────────────────────────────────── */
function timeAgo(iso) {
  if (!iso) return "";
  try {
    const m = Math.floor((Date.now() - new Date(iso)) / 60000);
    if (m < 1)  return "just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  } catch { return ""; }
}

/* ─── Bias arc (SVG) — back face ─────────────────────
   A thin arc that fills proportionally to the bias score,
   coloured by sentiment. Renders on the card's back face.
──────────────────────────────────────────────────────── */
function BiasArc({ score, label }) {
  const lc    = (label || "neutral").toLowerCase();
  const color = lc === "bullish" ? "#4ade80" : lc === "bearish" ? "#f87171" : "#d4af37";
  const r     = 36;
  const circ  = 2 * Math.PI * r;
  const fill  = circ * (1 - score / 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <div style={{ position: "relative", width: 90, height: 90 }}>
        <svg viewBox="0 0 90 90" style={{ transform: "rotate(-90deg)", width: 90, height: 90, position: "absolute", inset: 0 }}>
          <circle cx="45" cy="45" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="6" />
          <circle cx="45" cy="45" r={r} fill="none"
            stroke={color} strokeWidth="6"
            strokeDasharray={circ}
            strokeDashoffset={fill}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.8s ease 0.3s" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 500, color, lineHeight: 1 }}>
            {score}
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 7, color: "rgba(255,255,255,0.3)", letterSpacing: 1 }}>
            BIAS
          </span>
        </div>
      </div>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: 2,
        textTransform: "uppercase", color,
        padding: "3px 10px", borderRadius: 100,
        border: `1px solid ${color}44`, background: `${color}12`,
      }}>
        {label || "Neutral"}
      </span>
    </div>
  );
}

/* ─── NewsCard ──────────────────────────────────────── */
export default function NewsCard({ item, index = 0 }) {
  const [isRead,   setIsRead]   = useState(false);
  const [flipped,  setFlipped]  = useState(false);
  const cardRef = useRef(null);

  useEffect(() => {
    if (item.url) setIsRead(getReadSet().has(item.url));
  }, [item.url]);

  const handleRead = useCallback((e) => {
    e.preventDefault();             // prevent immediate navigation
    if (!item.url) return;

    // Flip the card — reveal back face with insight
    setFlipped(true);
    markRead(item.url);
    setIsRead(true);

    // After 1.8s (user reads back face), navigate
    setTimeout(() => {
      window.open(item.url, "_blank", "noopener,noreferrer");
      // Flip back after opening
      setTimeout(() => setFlipped(false), 400);
    }, 1800);
  }, [item.url]);

  // Click outside or press Escape to un-flip without navigating
  useEffect(() => {
    if (!flipped) return;
    const onKey = (e) => { if (e.key === "Escape") setFlipped(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flipped]);

  const label = item.label || "Neutral";
  const bias  = typeof item.bias === "number" ? item.bias : parseFloat(item.bias) || 50;
  const lc    = label.toLowerCase();

  return (
    <div
      ref={cardRef}
      className="flip-container"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className={`flip-inner${flipped ? " is-flipped" : ""}`}>

        {/* ═══ FRONT FACE ═══════════════════════════════ */}
        <div className={`flip-face flip-front news-card card-${lc}${isRead ? " card-read" : ""}`}>

          {/* Source + time / read indicator */}
          <div className="card-meta">
            <span className="card-source">{item.source || "Markets"}</span>
            {isRead
              ? <span className="card-read-tag">✓ Read</span>
              : <span className="card-time">{timeAgo(item.published)}</span>
            }
          </div>

          <h3 className={isRead ? "title-read" : ""}>{item.title}</h3>

          <div className={`bias-badge ${lc}`}>
            <span className="badge-dot" />
            {label} · {bias}%
          </div>

          <div className="bias-bar-wrap">
            <div className={`bias-bar-fill ${lc}`} style={{ width: `${bias}%` }} />
          </div>

          {item.summary && <p>{item.summary}</p>}

          {/* CTA — triggers flip */}
          <a href={item.url} onClick={handleRead}>
            {isRead ? "Read again →" : "Read full story →"}
          </a>
        </div>

        {/* ═══ BACK FACE ════════════════════════════════ */}
        <div className="flip-face flip-back">
          {/* Bias arc */}
          <BiasArc score={bias} label={label} />

          {/* Source */}
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 9,
            letterSpacing: 2, textTransform: "uppercase",
            color: "rgba(255,255,255,0.3)", marginTop: 12,
          }}>
            {item.source || "Markets"}
          </div>

          {/* AI insight */}
          {item.insight && (
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 11,
              color: "#d4af37", lineHeight: 1.7,
              borderLeft: "2px solid #d4af37",
              paddingLeft: 10, marginTop: 12,
              opacity: 0.85, textAlign: "left",
            }}>
              {item.insight}
            </div>
          )}

          {/* Title (compact) */}
          <p style={{
            fontFamily: "var(--font-display)", fontSize: 13,
            color: "rgba(226,232,240,0.7)", lineHeight: 1.5,
            marginTop: 12, fontWeight: 400,
          }}>
            {item.title?.slice(0, 80)}{item.title?.length > 80 ? "…" : ""}
          </p>

          {/* Opening indicator */}
          <div style={{
            marginTop: "auto",
            fontFamily: "var(--font-mono)", fontSize: 9,
            letterSpacing: 2, color: "rgba(255,255,255,0.25)",
            textTransform: "uppercase",
          }}>
            Opening article…
          </div>
        </div>

      </div>
    </div>
  );
}