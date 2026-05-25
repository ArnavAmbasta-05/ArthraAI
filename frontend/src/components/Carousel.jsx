import { API } from "../config";
// eslint-disable-next-line no-unused-vars
import { useEffect, useState, useRef } from "react";

const LABEL_COLOR = {
  Bullish: "#4ade80",
  Bearish: "#f87171",
  Neutral: "#64748b",
};

// Fallback shown while backend warms up
const FALLBACK = [
  { title: "RBI holds repo rate steady amid global uncertainty",      label: "Neutral" },
  { title: "Nifty 50 inches toward all-time high on FII inflows",    label: "Bullish" },
  { title: "Adani Group reports record quarterly revenue",            label: "Bullish" },
  { title: "IT sector outperforms as dollar strengthens vs rupee",   label: "Bullish" },
  { title: "Gold surges past ₹72,000 per 10g on safe-haven demand",  label: "Bearish" },
  { title: "Fed signals two rate cuts possible before year-end",      label: "Neutral" },
  { title: "China export data disappoints; global markets slip",      label: "Bearish" },
  { title: "Infosys raises FY25 revenue guidance on deal wins",       label: "Bullish" },
];

export default function Carousel() {
  const [news,    setNews]    = useState(FALLBACK);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // /news/carousel returns all 24h articles
    fetch(`${API}/news/carousel`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setNews(data);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));

    // Refresh every 2 minutes
    const id = setInterval(() => {
      fetch(`${API}/news/carousel`)
        .then(r => r.json())
        .then(d => { if (Array.isArray(d) && d.length > 0) setNews(d); })
        .catch(() => {});
    }, 120_000);

    return () => clearInterval(id);
  }, []);

  // Duplicate for seamless infinite scroll
  const doubled = [...news, ...news];

  return (
    <div className="carousel-box">
      <div className="carousel-header">
        {loading ? "Connecting…" : `${news.length} Headlines · 24h`}
      </div>
      <div className="carousel-scroll-area">
        <div className="carousel-track">
          {doubled.map((n, i) => (
            <div key={i} className="carousel-item">
              <span
                className="carousel-dot"
                style={{ background: LABEL_COLOR[n.label] || "#64748b" }}
              />
              <span>{n.title}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}