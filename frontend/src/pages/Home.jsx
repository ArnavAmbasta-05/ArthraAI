import { API } from "../config";
import { useEffect, useState, useCallback, useRef } from "react";
import Market  from "../components/Market";
import Carousel from "../components/Carousel";

/* ─── Clocks ─────────────────────────────────────────── */
const CLOCKS = [
  { city: "Mumbai",   zone: "Asia/Kolkata",     flag: "🇮🇳", abbr: "IST" },
  { city: "New York", zone: "America/New_York", flag: "🇺🇸", abbr: "EST" },
  { city: "Tokyo",    zone: "Asia/Tokyo",       flag: "🇯🇵", abbr: "JST" },
];

function useLiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

/* ─── 3D tilt hook ───────────────────────────────────── */
function useTilt(maxDeg = 8) {
  const ref      = useRef(null);
  const frameRef = useRef(null);
  const [style, setStyle] = useState({});

  const onMove = useCallback((e) => {
    cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const dx   = ((e.clientX - rect.left) / rect.width  - 0.5) * 2;
      const dy   = ((e.clientY - rect.top)  / rect.height - 0.5) * 2;
      setStyle({
        transform:  `perspective(600px) rotateY(${dx * maxDeg}deg) rotateX(${-dy * maxDeg}deg) translateZ(3px)`,
        transition: "transform 0.08s ease-out",
      });
    });
  }, [maxDeg]);

  const onLeave = useCallback(() => {
    cancelAnimationFrame(frameRef.current);
    setStyle({
      transform:  "perspective(600px) rotateY(0deg) rotateX(0deg) translateZ(0)",
      transition: "transform 0.5s cubic-bezier(0.22,1,0.36,1)",
    });
  }, []);

  return { ref, style, onMouseMove: onMove, onMouseLeave: onLeave };
}

/* ─── Count-up hook ──────────────────────────────────── */
function useCountUp(target, duration = 900) {
  const [val, setVal]     = useState(0);
  const [active, setActive] = useState(false);
  const ref  = useRef(null);

  // IntersectionObserver triggers the count when element enters viewport
  useEffect(() => {
    if (target === null || target === undefined) return;
    const el = ref.current;
    if (!el) return;

    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setActive(true);
        obs.disconnect();
      }
    }, { threshold: 0.4 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [target]);

  useEffect(() => {
    if (!active || !target) return;
    const num  = parseFloat(String(target).replace(/[^0-9.]/g, ""));
    if (isNaN(num)) { setVal(target); return; }

    const start = performance.now();
    const tick  = (now) => {
      const p = Math.min((now - start) / duration, 1);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(ease * num));
      if (p < 1) requestAnimationFrame(tick);
      else setVal(num);
    };
    requestAnimationFrame(tick);
  }, [active, target, duration]);

  return { ref, val };
}

/* ─── World clock card ───────────────────────────────── */
function WorldClock({ city, zone, flag, abbr }) {
  const now    = useLiveClock();
  const tilt   = useTilt(6);

  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone, hour: "2-digit", minute: "2-digit",
    second: "2-digit", hour12: false,
  }).formatToParts(now);

  const datePart = new Intl.DateTimeFormat("en-US", {
    timeZone: zone, weekday: "short", month: "short", day: "numeric",
  }).format(now);

  const get  = (t) => parts.find(p => p.type === t)?.value ?? "00";
  const H    = get("hour");
  const M    = get("minute");
  const S    = get("second");
  const h24  = parseInt(H, 10);

  const isOpen = zone === "Asia/Kolkata"    ? (h24 >= 9 && h24 < 16)
               : zone === "America/New_York" ? (h24 >= 9 && h24 < 16)
               :                               (h24 >= 9 && h24 < 15);
  const sessionColor = isOpen ? "var(--green)" : "var(--muted)";

  return (
    <div
      ref={tilt.ref}
      style={{
        ...tilt.style,
        background: "rgba(10,18,40,0.45)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "20px 24px",
        display: "flex", flexDirection: "column", gap: 6,
        position: "relative", overflow: "hidden",
        willChange: "transform", cursor: "default",
      }}
      onMouseMove={tilt.onMouseMove}
      onMouseLeave={tilt.onMouseLeave}
    >
      {/* Session-coloured top line */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${sessionColor}66, transparent)`,
      }} />

      {/* City + open/closed */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>{flag}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "var(--muted)" }}>
            {city}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%", background: sessionColor,
            boxShadow: isOpen ? `0 0 6px ${sessionColor}` : "none",
            animation: isOpen ? "liveBlink 1.4s ease-in-out infinite" : "none",
          }} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: 1.5, color: sessionColor }}>
            {isOpen ? "OPEN" : "CLOSED"}
          </span>
        </div>
      </div>

      {/* Digital time */}
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 500, letterSpacing: -0.5, lineHeight: 1 }}>
        {H}
        <span style={{ color: "var(--muted)", animation: "colonBlink 1s step-end infinite" }}>:</span>
        {M}
        <span style={{ fontSize: 16, color: "var(--muted)", marginLeft: 4 }}>{S}</span>
      </div>

      {/* TZ + date */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: 2, color: "var(--gold)" }}>{abbr}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--muted)", letterSpacing: 0.5 }}>{datePart}</span>
      </div>
    </div>
  );
}

/* ─── Stat item with count-up ────────────────────────── */
function StatItem({ label, value, isLive }) {
  const isNum = typeof value === "number";
  const { ref, val } = useCountUp(isNum ? value : null, 1000);

  return (
    <div className="stat-item" ref={ref}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {isLive ? (
          value
        ) : isNum ? (
          val
        ) : (
          value ?? "—"
        )}
      </div>
    </div>
  );
}

/* ─── Home page ──────────────────────────────────────── */
export default function Home({ setPage }) {
  const [ticker, setTicker] = useState([]);
  const [status, setStatus] = useState(null);

  const fetchTicker = useCallback(() => {
    fetch(`${API}/ticker`)
      .then(r => r.json())
      .then(d => { if (Array.isArray(d) && d.length > 0) setTicker(d); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchTicker();
    const id = setInterval(fetchTicker, 30_000);
    return () => clearInterval(id);
  }, [fetchTicker]);

  useEffect(() => {
    fetch(`${API}/status`)
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {});
  }, []);

  const doubled = ticker.length > 0 ? [...ticker, ...ticker] : [];

  const lastUpdated = (() => {
    if (!status?.last_updated) return "—";
    try { return new Date(status.last_updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
    catch { return "—"; }
  })();

  return (
    <div className="home">

      {/* ── Ticker ───────────────────────────────────── */}
      <div className="ticker-bar">
        <div className="ticker-live-badge">
          <span className="ticker-live-dot" />
          Live
        </div>
        {doubled.length > 0 ? (
          <div className="ticker-track">
            {doubled.map((t, i) => (
              <div key={i} className="ticker-item">
                <span className="ticker-name">{t.name}</span>
                <span className="ticker-sep">·</span>
                <span className="ticker-val">{t.price}</span>
                <span className={`ticker-chg ${t.up ? "up" : "down"}`}>
                  {t.up ? "▲" : "▼"} {t.change}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--muted)", padding: "0 24px", letterSpacing: "1px" }}>
            Connecting to live market data…
          </span>
        )}
      </div>

      {/* ── Hero ─────────────────────────────────────── */}
      <section className="hero-grid">
        <div className="hero-left">
          <div className="hero-eyebrow">Financial Intelligence</div>
          <h1>Markets.<br /><em>Decoded</em> by AI.</h1>
          <p>Real-time sentiment analysis across financial sources. Know the bias before the market moves.</p>
          <div className="live-dot">LIVE ANALYSIS</div>

          <div style={{ marginTop: "32px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <button
              onClick={() => setPage("news")}
              className="btn-primary"
              onMouseOver={e => e.currentTarget.style.boxShadow = "0 0 28px rgba(212,175,55,0.45)"}
              onMouseOut={e  => e.currentTarget.style.boxShadow = "none"}
            >
              View Markets →
            </button>
            <button onClick={() => setPage("bias")} className="btn-ghost">
              Bias System
            </button>
          </div>
        </div>

        <div className="hero-center"><Market /></div>
        <div className="hero-right"><Carousel /></div>
      </section>

      {/* ── World Clocks ─────────────────────────────── */}
      <div style={{ padding: "28px 48px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "2.5px", textTransform: "uppercase", color: "var(--muted)", marginBottom: "14px", display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ width: 20, height: 1, background: "var(--gold)", display: "inline-block" }} />
          Global Market Hours
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
          {CLOCKS.map(c => <WorldClock key={c.city} {...c} />)}
        </div>
      </div>

      {/* ── Stat Strip — count-up on enter ───────────── */}
      <div className="stat-strip">
        <StatItem label="Sources Tracked"  value={4} />
        <StatItem label="Articles Cached"  value={status?.cached_articles ?? null} />
        <StatItem label="Cache Status" isLive value={
          status?.status === "warming_up"
            ? <span style={{ color: "var(--gold)", fontSize: 14 }}>Warming…</span>
            : <span style={{ color: "var(--green)", fontSize: 14 }}>● Live</span>
        } />
        <StatItem label="Last Refreshed" isLive value={
          <span style={{ fontSize: 16 }}>{lastUpdated}</span>
        } />
      </div>

    </div>
  );
}
