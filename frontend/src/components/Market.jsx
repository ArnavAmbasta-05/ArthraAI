import { API } from "../config";
import { useEffect, useState, useRef, useCallback } from "react";

/* ─── 3D tilt hook ───────────────────────────────────────
   Tracks mouse position relative to card center.
   Returns inline style with perspective + rotateX/Y.
   Max tilt: ±12°. Resets smoothly on mouse leave.
──────────────────────────────────────────────────────── */
function useTilt(maxDeg = 12) {
  const ref       = useRef(null);
  const frameRef  = useRef(null);
  const [style, setStyle] = useState({});

  const onMove = useCallback((e) => {
    cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      const el   = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const cx   = rect.left + rect.width  / 2;
      const cy   = rect.top  + rect.height / 2;
      const dx   = (e.clientX - cx) / (rect.width  / 2); // -1 to 1
      const dy   = (e.clientY - cy) / (rect.height / 2); // -1 to 1
      setStyle({
        transform:  `perspective(900px) rotateY(${dx * maxDeg}deg) rotateX(${-dy * maxDeg}deg) translateZ(4px)`,
        transition: "transform 0.08s ease-out",
        boxShadow:  `${-dx * 10}px ${dy * 10}px 40px rgba(212,175,55,0.12)`,
      });
    });
  }, [maxDeg]);

  const onLeave = useCallback(() => {
    cancelAnimationFrame(frameRef.current);
    setStyle({
      transform:  "perspective(900px) rotateY(0deg) rotateX(0deg) translateZ(0px)",
      transition: "transform 0.5s cubic-bezier(0.22,1,0.36,1), box-shadow 0.5s ease",
      boxShadow:  "none",
    });
  }, []);

  return { ref, style, onMouseMove: onMove, onMouseLeave: onLeave };
}

/* ─── Market component ───────────────────────────────── */
export default function Market() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const niftyTilt = useTilt(10);
  const spTilt    = useTilt(10);

  useEffect(() => {
    fetch(`${API}/market`)
      .then(res => res.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));

    const id = setInterval(() => {
      fetch(`${API}/market`)
        .then(r => r.json())
        .then(setData)
        .catch(() => {});
    }, 30_000);

    return () => clearInterval(id);
  }, []);

  const niftyDir = data?.sensex_up === false ? "down" : "up";
  const spDir    = data?.sp_up     === false ? "down" : "up";

  return (
    <div className="market-center">
      {/* ── Nifty 50 — tilt on hover ── */}
      <div
        ref={niftyTilt.ref}
        className="glass-card sensex-box"
        style={{ ...niftyTilt.style, willChange: "transform" }}
        onMouseMove={niftyTilt.onMouseMove}
        onMouseLeave={niftyTilt.onMouseLeave}
      >
        {/* Terminal-style corner brackets */}
        <span className="corner-tl" />
        <span className="corner-br" />
        <div className="market-label">India — Nifty 50</div>
        <h1 style={{ opacity: loading ? 0.35 : 1, transition: "opacity 0.4s" }}>
          {data?.sensex ?? "—"}
        </h1>
        <div className={`market-change ${niftyDir}`}>
          {data?.sensex_change ?? (loading ? "Fetching…" : "N/A")}
        </div>
      </div>

      {/* ── S&P 500 — tilt on hover ── */}
      <div
        ref={spTilt.ref}
        className="glass-card sp-box"
        style={{ ...spTilt.style, willChange: "transform" }}
        onMouseMove={spTilt.onMouseMove}
        onMouseLeave={spTilt.onMouseLeave}
      >
        <div className="market-label">USA — S&P 500</div>
        <h2 style={{ opacity: loading ? 0.35 : 1, transition: "opacity 0.4s" }}>
          {data?.sp500 ?? "—"}
        </h2>
        <div className={`market-change ${spDir}`}>
          {data?.sp_change ?? (loading ? "Fetching…" : "N/A")}
        </div>
      </div>
    </div>
  );
}