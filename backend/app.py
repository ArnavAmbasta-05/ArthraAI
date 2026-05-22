from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sources import fetch_all_news
from ai import process_news, score_bias, KEYWORD_CATEGORIES
from bias import analyze_bias
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import yfinance as yf
import asyncio
import os

# ═══════════════════════════════════════════════════
# CORS ORIGINS
# Reads from environment variable on Railway.
# Falls back to localhost for local development.
# ═══════════════════════════════════════════════════
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    FRONTEND_URL,
]

# ═══════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(update_news_cache())
    yield

app = FastAPI(
    title="Arthra API",
    description="Financial news + bias scoring backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════
# CACHES
# ═══════════════════════════════════════════════════
NEWS_CACHE: list[dict] = []
LAST_UPDATED           = None


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════
def remove_duplicates(articles: list[dict]) -> list[dict]:
    seen, unique = set(), []
    for a in articles:
        t = a["title"].strip().lower()
        if t not in seen:
            seen.add(t)
            unique.append(a)
    return unique


def _safe_attr(obj, attr: str, default=0):
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _fmt_change(price: float, prev: float):
    if not prev:
        return "N/A", True
    diff  = price - prev
    pct   = (diff / prev) * 100
    sign  = "+" if diff >= 0 else ""
    arrow = "▲" if diff >= 0 else "▼"
    return f"{arrow} {sign}{diff:,.2f}  ({sign}{pct:.2f}%)", diff >= 0


# ═══════════════════════════════════════════════════
# CATEGORY TAGGER
# ═══════════════════════════════════════════════════
_INDIA_TERMS = {
    "india","indian","rbi","rupee","sebi","bse","nse","nifty","sensex",
    "modi","dalal","mumbai","delhi","bengaluru","ipo","sip","inr","₹",
}
_INDIA_STOCK_TERMS = {
    "reliance","tcs","infosys","wipro","hdfc","icici","axis bank","sbi",
    "bajaj","airtel","adani","tata","mahindra","maruti","ongc","itc",
}
_INTL_STOCK_TERMS = {
    "apple","microsoft","nvidia","tesla","google","alphabet","amazon",
    "meta","jpmorgan","goldman","dow jones","s&p","nasdaq","sp500",
    "nyse","stock","shares","equity","earnings","ipo","etf","dividend",
}
_GLOBAL_EXCL_INDIA = {
    "fed","federal reserve","ecb","boe","china","usa","us economy",
    "europe","eurozone","dollar","yen","euro","pound","yuan",
    "wall street","london","frankfurt","treasury","fomc","powell",
    "inflation","recession","gdp","global","world economy",
    "opec","crude","brent","wti",
}


def _categorize(title: str, summary: str) -> list[str]:
    text = (title + " " + summary).lower()
    cats = ["all"]
    has_india       = any(t in text for t in _INDIA_TERMS)
    has_india_stock = any(t in text for t in _INDIA_STOCK_TERMS)
    has_intl_stock  = any(t in text for t in _INTL_STOCK_TERMS)
    has_global_excl = any(t in text for t in _GLOBAL_EXCL_INDIA)

    if has_india_stock or has_intl_stock:
        cats.append("stocks")
    if has_india:
        cats.append("india")
    if has_global_excl and not (has_india and not has_intl_stock and not has_global_excl):
        cats.append("global")
    return cats


# ═══════════════════════════════════════════════════
# BACKGROUND NEWS CACHE
# ═══════════════════════════════════════════════════
async def update_news_cache():
    global NEWS_CACHE, LAST_UPDATED

    while True:
        try:
            print("🔄 Updating news cache...")
            articles = remove_duplicates(fetch_all_news())
            now      = datetime.now(timezone.utc)
            final    = []

            for a in articles:
                try:
                    t = datetime.fromisoformat(a["published"])
                except (ValueError, KeyError):
                    continue
                if t < now - timedelta(hours=24):
                    continue

                text = a.get("summary", "")
                ai   = await asyncio.to_thread(process_news, text[:800])

                final.append({
                    "title":      a["title"],
                    "summary":    ai["summary"],
                    "bias":       ai["bias"],
                    "label":      ai["label"],
                    "insight":    ai["insight"],
                    "url":        a["url"],
                    "published":  a["published"],
                    "source":     a["source"],
                    "categories": _categorize(a["title"], a.get("summary", "")),
                })

            final.sort(key=lambda x: x["published"], reverse=True)
            NEWS_CACHE   = final
            LAST_UPDATED = datetime.now(timezone.utc)
            print(f"✅ Cached {len(NEWS_CACHE)} articles")

        except Exception as e:
            print(f"❌ Cache error: {e}")

        await asyncio.sleep(60)


# ═══════════════════════════════════════════════════
# TICKER SYMBOLS
# ═══════════════════════════════════════════════════
TICKER_SYMBOLS = [
    ("^BSESN",       "SENSEX"),
    ("^IXIC",        "NASDAQ"),
    ("^N225",        "NIKKEI 225"),
    ("GC=F",         "GOLD"),
    ("SI=F",         "SILVER"),
    ("CL=F",         "CRUDE OIL"),
    ("RELIANCE.NS",  "RELIANCE"),
    ("HDFCBANK.NS",  "HDFC BANK"),
    ("AAPL",         "APPLE"),
    ("TSLA",         "TESLA"),
    ("^BSESN",       "SENSEX"),
]


# ═══════════════════════════════════════════════════
# HEALTH CHECK — Railway uses this to verify the app started
# ═══════════════════════════════════════════════════
@app.get("/")
def root():
    return {"status": "ok", "app": "Arthra API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}


# ═══════════════════════════════════════════════════
# TICKER  /ticker
# ═══════════════════════════════════════════════════
@app.get("/ticker")
def ticker():
    results = []
    for symbol, label in TICKER_SYMBOLS:
        try:
            info      = yf.Ticker(symbol).fast_info
            price     = _safe_attr(info, "last_price", 0)
            prev      = _safe_attr(info, "previous_close", 0)
            if not price:
                continue
            change_str, is_up = _fmt_change(price, prev)
            results.append({
                "name":   label,
                "price":  f"{price:,.2f}",
                "change": change_str,
                "up":     is_up,
            })
        except Exception as e:
            print(f"⚠️ Ticker {symbol}: {e}")
    return results


# ═══════════════════════════════════════════════════
# MARKET  /market
# ═══════════════════════════════════════════════════
@app.get("/market")
def market():
    try:
        n_info  = yf.Ticker("^NSEI").fast_info
        sp_info = yf.Ticker("^GSPC").fast_info

        n_price  = _safe_attr(n_info,  "last_price",     0)
        sp_price = _safe_attr(sp_info, "last_price",     0)
        n_prev   = _safe_attr(n_info,  "previous_close", 0)
        sp_prev  = _safe_attr(sp_info, "previous_close", 0)

        n_chg,  n_up  = _fmt_change(n_price,  n_prev)
        sp_chg, sp_up = _fmt_change(sp_price, sp_prev)

        return {
            "sensex":        f"{n_price:,.2f}",
            "sp500":         f"{sp_price:,.2f}",
            "sensex_change": n_chg,
            "sp_change":     sp_chg,
            "sensex_up":     n_up,
            "sp_up":         sp_up,
        }
    except Exception as e:
        print(f"❌ Market error: {e}")
        return {
            "sensex":        "22,519.40",
            "sp500":         "5,214.08",
            "sensex_change": "▲ +112.30  (+0.50%)",
            "sp_change":     "▲ +22.40  (+0.43%)",
            "sensex_up":     True,
            "sp_up":         True,
        }


# ═══════════════════════════════════════════════════
# CAROUSEL  /news/carousel
# ═══════════════════════════════════════════════════
@app.get("/news/carousel")
def carousel():
    return [
        {"title": a["title"], "label": a["label"],
         "bias": a["bias"], "source": a["source"]}
        for a in NEWS_CACHE
    ]


# ═══════════════════════════════════════════════════
# NEWS  /news/latest
# ═══════════════════════════════════════════════════
@app.get("/news/latest")
def news(topic: str = "all"):
    if not NEWS_CACHE:
        return []
    topic = topic.lower().strip()
    if topic == "all":
        return NEWS_CACHE
    return [a for a in NEWS_CACHE if topic in a.get("categories", [])]


# ═══════════════════════════════════════════════════
# BIAS ENDPOINTS
# ═══════════════════════════════════════════════════
class AnalyzeRequest(BaseModel):
    text: str

@app.post("/bias/analyze")
async def bias_analyze(req: AnalyzeRequest):
    if not req.text or not req.text.strip():
        return {"error": "No text provided"}
    result = await asyncio.to_thread(analyze_bias, req.text[:1000])
    return result

@app.get("/bias/keywords")
def bias_keywords():
    return KEYWORD_CATEGORIES


# ═══════════════════════════════════════════════════
# STATUS  /status
# ═══════════════════════════════════════════════════
@app.get("/status")
def status():
    return {
        "cached_articles": len(NEWS_CACHE),
        "last_updated":    LAST_UPDATED,
        "status":          "ok" if NEWS_CACHE else "warming_up",
    }