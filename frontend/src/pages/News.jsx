import { API } from "../config";
import { useEffect, useState, useMemo } from "react";
import NewsCard from "../components/NewsCard";

// UI label → backend topic param (must match app.py exactly)
const FILTERS = [
  {
    label: "All",
    topic: "all",
    desc:  "All financial news from the last 24 hours",
  },
  {
    label: "Stocks",
    topic: "stocks",
    desc:  "Indian & international company stocks, equities, earnings",
  },
  {
    label: "India",
    topic: "india",
    desc:  "Indian markets, RBI, Sensex, Nifty — news that affects Indian investors",
  },
  {
    label: "Global",
    topic: "global",
    desc:  "Global markets, Fed, international economies — ex-India focus",
  },
];

export default function News() {
  const [news,    setNews]    = useState([]);
  const [topic,   setTopic]   = useState("all");
  const [query,   setQuery]   = useState("");
  const [loading, setLoading] = useState(true);
  const [warming, setWarming] = useState(false);

  // Fetch from backend on topic change
  useEffect(() => {
    setLoading(true);
    setWarming(false);

    fetch(`${API}/news/latest?topic=${topic}`)
      .then(res => res.json())
      .then(data => {
        const arr = Array.isArray(data) ? data : [];
        setNews(arr);
        setWarming(arr.length === 0);
        setLoading(false);
      })
      .catch(() => {
        setNews([]);
        setLoading(false);
      });
  }, [topic]);

  // Client-side search filter on top of topic results
  const filtered = useMemo(() => {
    if (!query.trim()) return news;
    const q = query.toLowerCase();
    return news.filter(n =>
      n.title?.toLowerCase().includes(q)   ||
      n.summary?.toLowerCase().includes(q) ||
      n.source?.toLowerCase().includes(q)  ||
      n.label?.toLowerCase().includes(q)
    );
  }, [news, query]);

  const activeFilter = FILTERS.find(f => f.topic === topic);

  return (
    <section className="news-section">
      <div className="section-header" data-num="01">
        <h2>AI News</h2>
        <p>
          {activeFilter?.desc ?? "Real-time AI sentiment analysis across financial sources"}
        </p>
      </div>

      {/* Search bar */}
      <div className="search-wrap">
        <div className="search-box">
          <span className="search-icon">⌕</span>
          <input
            type="text"
            placeholder="Search by headline, source, or sentiment…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              style={{
                background: "none",
                border: "none",
                color: "var(--muted)",
                cursor: "pointer",
                fontSize: "16px",
                lineHeight: 1,
                flexShrink: 0,
              }}
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="filters">
        {FILTERS.map(({ label, topic: t }) => (
          <button
            key={t}
            className={topic === t ? "active" : ""}
            onClick={() => { setTopic(t); setQuery(""); }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Results count */}
      {!loading && !warming && filtered.length > 0 && (
        <div style={{
          padding: "12px 48px",
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          color: "var(--muted)",
          letterSpacing: "1px",
          borderBottom: "1px solid var(--border)",
        }}>
          {filtered.length} {filtered.length === 1 ? "article" : "articles"}
          {query && ` matching "${query}"`}
        </div>
      )}

      {/* Grid */}
      <div className="news-grid">
        {loading ? (
          <div className="news-empty">Loading articles…</div>
        ) : warming ? (
          <div className="news-empty">
            Cache warming up — please check back in a moment.
          </div>
        ) : filtered.length === 0 ? (
          <div className="news-empty">
            {query
              ? `No results for "${query}"`
              : "No articles found for this filter."
            }
          </div>
        ) : (
          filtered.map((n, i) => <NewsCard key={i} item={n} index={i} />)
        )}
      </div>
    </section>
  );
}