import re
import socket
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ─── Global defaults ──────────────────────────────────────
feedparser.USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
socket.setdefaulttimeout(12)

_UA = feedparser.USER_AGENT

_BASE_HEADERS = {
    "User-Agent":      _UA,
    "Accept":          "text/html,application/xhtml+xml,application/xml,"
                       "application/rss+xml,application/atom+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control":   "no-cache",
}

_SESSION = requests.Session()
_SESSION.headers.update(_BASE_HEADERS)


# ─── HTML cleaner ─────────────────────────────────────────
def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return (clean
            .replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"')
            .replace("&#39;", "'").replace("&nbsp;", " "))


# ─── Strategy 1: feedparser ───────────────────────────────
def _fetch_rss_feedparser(url: str, extra: dict = None) -> list:
    headers = {**_BASE_HEADERS, **(extra or {})}
    feed    = feedparser.parse(url, request_headers=headers)
    return feed.entries if feed.entries else []


# ─── Strategy 2: requests → feedparser ───────────────────
def _fetch_rss_requests(url: str, extra: dict = None) -> list:
    headers = {**_BASE_HEADERS, **(extra or {})}
    r       = _SESSION.get(url, headers=headers, timeout=12)
    r.raise_for_status()
    feed    = feedparser.parse(r.text)
    return feed.entries if feed.entries else []


# ─── Entry → article dict ─────────────────────────────────
def _entry_to_article(entry, source_name: str, cutoff: datetime) -> dict | None:
    pub_time = None
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                pub_time = datetime(*parsed[:6], tzinfo=timezone.utc)
                break
            except (TypeError, ValueError):
                pass
    if pub_time is None:
        pub_time = datetime.now(timezone.utc)
    if pub_time < cutoff:
        return None

    raw = entry.get("summary", "") or entry.get("description", "") or ""
    return {
        "title":     (entry.get("title", "") or "").strip(),
        "summary":   _strip_html(raw)[:800],
        "source":    source_name,
        "url":       entry.get("link", ""),
        "published": pub_time.isoformat(),
    }


def _entries_to_articles(entries, source_name: str, cutoff: datetime, limit: int = 25) -> list:
    out = []
    for e in entries[:limit]:
        a = _entry_to_article(e, source_name, cutoff)
        if a and a["title"]:
            out.append(a)
    return out




# ─── Source registry ──────────────────────────────────────
# strategy: "feedparser" | "requests"
# fallback:  try the other if primary returns nothing
_RSS_SOURCES = [
    {
        "name":    "The Hindu Business",
        "urls":    [
            "https://www.thehindu.com/business/feeder/default.rss",
            "https://www.thehindu.com/business/Economy/feeder/default.rss",
            "https://www.thehindu.com/business/markets/feeder/default.rss",
        ],
        "extra":    {"Referer": "https://www.thehindu.com/"},
        "strategy": "feedparser",
    },
    {
        "name":    "Mint Markets",
        "urls":    [
            "https://www.livemint.com/rss/markets",
            "https://www.livemint.com/rss/companies",
            "https://www.livemint.com/rss/economy",
        ],
        "extra":    {"Referer": "https://www.livemint.com/"},
        "strategy": "feedparser",
    },
    {
        "name":    "Business Line",
        "urls":    [
            "https://www.thehindubusinessline.com/markets/feeder/default.rss",
            "https://www.thehindubusinessline.com/economy/feeder/default.rss",
            "https://www.thehindubusinessline.com/news/feeder/default.rss",
            "https://www.thehindubusinessline.com/money-and-banking/feeder/default.rss",
        ],
        "extra":    {"Referer": "https://www.thehindubusinessline.com/"},
        "strategy": "feedparser",
        "fallback": "requests",
    },

]

_FETCHERS = {
    "feedparser": _fetch_rss_feedparser,
    "requests":   _fetch_rss_requests,
}


def _parse_rss_source(source: dict, cutoff: datetime) -> list[dict]:
    name     = source["name"]
    extra    = source.get("extra", {})
    primary  = source.get("strategy", "feedparser")
    fallback = source.get("fallback")

    for url in source["urls"]:
        order = [primary] + ([fallback] if fallback and fallback != primary else [])
        for strategy in order:
            try:
                entries  = _FETCHERS[strategy](url, extra)
                if not entries:
                    continue
                articles = _entries_to_articles(entries, name, cutoff)
                if articles:
                    print(f"  ✅ {name}: {len(articles)} articles [{strategy}]")
                    return articles
                print(f"  ⚠️  {name}: feed OK but 0 recent articles at {url}")
            except Exception as e:
                print(f"  ⚠️  {name} [{strategy}] {url}: {e}")

    print(f"  ✗ {name}: all URLs exhausted")
    return []


# ─── Public API ───────────────────────────────────────────
def fetch_all_news() -> list[dict]:
    cutoff       = datetime.now(timezone.utc) - timedelta(hours=24)
    all_articles = []

    print("📡 Fetching news sources...")

    for source in _RSS_SOURCES:
        all_articles.extend(_parse_rss_source(source, cutoff))


    print(f"📰 Total raw articles: {len(all_articles)}")
    return all_articles