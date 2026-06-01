"""
app.py — Arthra backend

Market data sources (in priority order):
  1. Finnhub free API  — stocks + forex (works from all server IPs, 60 calls/min free)
  2. NSE public API    — Nifty/Sensex direct from NSE (no auth needed)
  3. Fallback prices   — shown if both above fail (never blank UI)

Note: Yahoo Finance and Stooq both block Railway/cloud IPs.
Finnhub + NSE are the reliable alternatives.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sources import fetch_all_news
from ai import process_news, score_bias, KEYWORD_CATEGORIES
from bias import analyze_bias
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import asyncio
import os
import requests

# ═══════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════
# Get a free Finnhub API key at finnhub.io (takes 30 seconds)
# Set it in Railway dashboard → Variables → FINNHUB_KEY
FINNHUB_KEY  = os.environ.get("FINNHUB_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# ═══════════════════════════════════════════════════
# HTTP SESSION
# ═══════════════════════════════════════════════════
_S = requests.Session()
_S.headers.update({
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
})


# ═══════════════════════════════════════════════════
# MARKET DATA FETCHERS
# ═══════════════════════════════════════════════════

def _finnhub_quote(symbol: str) -> tuple[float, float]:
    """
    Fetch current price + previous close from Finnhub.
    Free tier: 60 calls/min, no IP restrictions.
    Returns (price, prev_close) or (0, 0) on failure.
    """
    if not FINNHUB_KEY:
        return 0.0, 0.0
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        r   = _S.get(url, timeout=8)
        r.raise_for_status()
        d   = r.json()
        c   = float(d.get("c", 0) or 0)   # current price
        pc  = float(d.get("pc", 0) or 0)  # previous close
        return (c, pc) if c > 0 else (0.0, 0.0)
    except Exception as e:
        print(f"  ⚠️  Finnhub {symbol}: {e}")
        return 0.0, 0.0


def _nse_indices() -> dict:
    """
    Fetch Nifty 50 + Sensex from NSE allIndices API.
    Also fetches RELIANCE and HDFCBANK via NSE equity quote API.
    No auth needed. Works from server IPs.
    """
    result = {}

    # ── Indices ───────────────────────────────────────────
    try:
        r = _S.get(
            "https://www.nseindia.com/api/allIndices",
            headers={
                **dict(_S.headers),
                "Referer": "https://www.nseindia.com/",
                "Origin":  "https://www.nseindia.com",
                "Host":    "www.nseindia.com",
            },
            timeout=8,
        )
        r.raise_for_status()
        for idx in r.json().get("data", []):
            name = idx.get("indexSymbol", "")
            last = float(idx.get("last", 0) or 0)
            prev = float(idx.get("previousClose", 0) or 0)
            if name == "NIFTY 50" and last > 0:
                result["NIFTY 50"] = (last, prev)
            elif name in ("S&P BSE SENSEX", "SENSEX") and last > 0:
                result["SENSEX"] = (last, prev)
    except Exception as e:
        print(f"  ⚠️  NSE indices: {e}")

    # ── Individual NSE stocks ─────────────────────────────
    nse_stocks = {
        "RELIANCE":  "RELIANCE",
        "HDFC BANK": "HDFCBANK",
    }
    for display_name, symbol in nse_stocks.items():
        try:
            r = _S.get(
                f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
                headers={
                    **dict(_S.headers),
                    "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
                    "Host":    "www.nseindia.com",
                },
                timeout=8,
            )
            r.raise_for_status()
            d    = r.json()
            last = float(d.get("priceInfo", {}).get("lastPrice", 0) or 0)
            prev = float(d.get("priceInfo", {}).get("previousClose", 0) or 0)
            if last > 0:
                result[display_name] = (last, prev)
        except Exception as e:
            print(f"  ⚠️  NSE {display_name}: {e}")

    return result


def _fmt(price: float, prev: float) -> tuple[str, bool]:
    if not prev or prev == 0:
        return "N/A", True
    diff  = price - prev
    pct   = (diff / prev) * 100
    sign  = "+" if diff >= 0 else ""
    arrow = "▲" if diff >= 0 else "▼"
    return f"{arrow} {sign}{diff:,.2f}  ({sign}{pct:.2f}%)", diff >= 0


# ═══════════════════════════════════════════════════
# PRICE CACHE + FALLBACKS
# ═══════════════════════════════════════════════════
_CACHE: dict = {}

_FALLBACK = {
    "SENSEX":     {"price": "74,339.44", "change": "▲ +482.10  (+0.65%)", "up": True},
    "NIFTY 50":   {"price": "22,519.40", "change": "▲ +112.30  (+0.50%)", "up": True},
    "NASDAQ":     {"price": "18,350.21", "change": "▲ +120.40  (+0.66%)", "up": True},
    "NIKKEI 225": {"price": "38,647.75", "change": "▲ +276.20  (+0.72%)", "up": True},
    "GOLD":       {"price": "2,346.80",  "change": "▲ +12.30   (+0.53%)", "up": True},
    "SILVER":     {"price": "29.42",     "change": "▲ +0.18    (+0.62%)", "up": True},
    "CRUDE OIL":  {"price": "82.14",     "change": "▼ -0.42    (-0.51%)", "up": False},
    "RELIANCE":   {"price": "2,947.30",  "change": "▲ +22.10   (+0.76%)", "up": True},
    "HDFC BANK":  {"price": "1,683.50",  "change": "▲ +8.40    (+0.50%)", "up": True},
    "APPLE":      {"price": "189.30",    "change": "▲ +1.20    (+0.64%)", "up": True},
    "TESLA":      {"price": "177.48",    "change": "▼ -2.30    (-1.28%)", "up": False},
    "S&P 500":    {"price": "5,214.08",  "change": "▲ +22.40   (+0.43%)", "up": True},
}

# Finnhub symbols for each display name
# Finnhub FREE tier symbols only
# US stocks: plain ticker — always free
# Commodities: use ETF proxies (GLD, SLV, USO) — free as US stocks
# Indian stocks: handled by NSE API separately
# NIKKEI: no free API exists — uses fallback
FINNHUB_MAP = {
    "S&P 500":   "SPY",   # SPDR S&P 500 ETF
    "NASDAQ":    "QQQ",   # Invesco QQQ (Nasdaq 100 ETF)
    "GOLD":      "GLD",   # SPDR Gold Shares ETF
    "SILVER":    "SLV",   # iShares Silver Trust ETF
    "CRUDE OIL": "USO",   # United States Oil Fund ETF
    "APPLE":     "AAPL",  # Apple Inc
    "TESLA":     "TSLA",  # Tesla Inc
    # NIKKEI 225 — no free API, stays on fallback
    # RELIANCE, HDFC BANK — handled by NSE API
    # SENSEX, NIFTY 50    — handled by NSE API
}

TICKER_ORDER = [
    "SENSEX", "NASDAQ", "NIKKEI 225", "GOLD", "SILVER",
    "CRUDE OIL", "RELIANCE", "HDFC BANK", "APPLE", "TESLA", "SENSEX",
]


async def refresh_ticker_cache():
    """
    Background task: refresh prices every 5 minutes.
    Uses NSE API for Indian indices, Finnhub for everything else.
    """
    while True:
        print("📈 Refreshing market prices...")

        # 1. Try NSE API for Indian indices (most reliable for India)
        nse = await asyncio.to_thread(_nse_indices)
        for name, (price, prev) in nse.items():
            change_str, is_up = _fmt(price, prev)
            _CACHE[name] = {"name": name, "price": f"{price:,.2f}",
                            "change": change_str, "up": is_up}
            print(f"  ✅ {name}: {price:,.2f} [NSE]")

        # 2. Finnhub for international symbols
        for name, symbol in FINNHUB_MAP.items():
            if name in _CACHE:
                continue  # already got it from NSE
            price, prev = await asyncio.to_thread(_finnhub_quote, symbol)
            if price > 0:
                change_str, is_up = _fmt(price, prev)
                _CACHE[name] = {"name": name, "price": f"{price:,.2f}",
                                "change": change_str, "up": is_up}
                print(f"  ✅ {name}: {price:,.2f} [Finnhub]")
            else:
                print(f"  ⚠️  {name}: no data — using fallback")
            await asyncio.sleep(1)

        print(f"✅ Ticker cache: {len(_CACHE)}/{len(_FALLBACK)} symbols live")
        await asyncio.sleep(300)  # refresh every 5 minutes


# ═══════════════════════════════════════════════════
# NEWS CACHE
# ═══════════════════════════════════════════════════
NEWS_CACHE:  list[dict] = []
LAST_UPDATED             = None


_INDIA_TERMS = {
    "india","indian","rbi","rupee","sebi","bse","nse","nifty","sensex",
    "modi","dalal","mumbai","delhi","bengaluru","ipo","sip","inr","₹",
}
_INDIA_STOCK = {
    "reliance","tcs","infosys","wipro","hdfc","icici","axis bank","sbi",
    "bajaj","airtel","adani","tata","mahindra","maruti","ongc","itc",
}
_INTL_STOCK = {
    "apple","microsoft","nvidia","tesla","google","alphabet","amazon",
    "meta","jpmorgan","goldman","dow jones","s&p","nasdaq","sp500",
    "nyse","stock","shares","equity","earnings","ipo","etf","dividend",
}
_GLOBAL = {
    "fed","federal reserve","ecb","boe","china","usa","us economy",
    "europe","eurozone","dollar","yen","euro","pound","yuan",
    "wall street","london","frankfurt","treasury","fomc","powell",
    "inflation","recession","gdp","global","world economy",
    "opec","crude","brent","wti",
}


def _categorize(title: str, summary: str) -> list[str]:
    text = (title + " " + summary).lower()
    cats = ["all"]
    if any(t in text for t in _INDIA_STOCK) or any(t in text for t in _INTL_STOCK):
        cats.append("stocks")
    if any(t in text for t in _INDIA_TERMS):
        cats.append("india")
    if any(t in text for t in _GLOBAL):
        cats.append("global")
    return cats


def _dedup(articles):
    seen, out = set(), []
    for a in articles:
        t = a["title"].strip().lower()
        if t not in seen:
            seen.add(t)
            out.append(a)
    return out


async def update_news_cache():
    global NEWS_CACHE, LAST_UPDATED
    while True:
        try:
            print("🔄 Fetching news...")
            articles = _dedup(fetch_all_news())
            now      = datetime.now(timezone.utc)
            final    = []
            for a in articles:
                try:
                    t = datetime.fromisoformat(a["published"])
                except (ValueError, KeyError):
                    continue
                if t < now - timedelta(hours=24):
                    continue
                ai = await asyncio.to_thread(process_news, a.get("summary", "")[:800])
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
            print(f"❌ News cache error: {e}")
        await asyncio.sleep(60)


# ═══════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(update_news_cache())
    asyncio.create_task(refresh_ticker_cache())
    yield

app = FastAPI(title="Arthra API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "ok", "app": "Arthra API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {
        "status":         "healthy",
        "news_cached":    len(NEWS_CACHE),
        "tickers_cached": len(_CACHE),
        "finnhub_key_set": bool(FINNHUB_KEY),
    }

@app.get("/ticker")
def ticker():
    seen, results = set(), []
    for name in TICKER_ORDER:
        if name in seen:
            continue
        seen.add(name)
        data = _CACHE.get(name) or {"name": name, **_FALLBACK[name]}
        results.append(data)
    return results

@app.get("/market")
def market():
    nifty = _CACHE.get("NIFTY 50") or _FALLBACK["NIFTY 50"]
    sp    = _CACHE.get("S&P 500")  or _FALLBACK["S&P 500"]
    return {
        "sensex":        nifty["price"],
        "sp500":         sp["price"],
        "sensex_change": nifty["change"],
        "sp_change":     sp["change"],
        "sensex_up":     nifty["up"],
        "sp_up":         sp["up"],
    }

@app.get("/news/carousel")
def carousel():
    return [{"title": a["title"], "label": a["label"],
             "bias": a["bias"],   "source": a["source"]}
            for a in NEWS_CACHE]

@app.get("/news/latest")
def news(topic: str = "all"):
    if not NEWS_CACHE:
        return []
    topic = topic.lower().strip()
    if topic == "all":
        return NEWS_CACHE
    return [a for a in NEWS_CACHE if topic in a.get("categories", [])]

class AnalyzeRequest(BaseModel):
    text: str

@app.post("/bias/analyze")
async def bias_analyze(req: AnalyzeRequest):
    if not req.text or not req.text.strip():
        return {"error": "No text provided"}
    return await asyncio.to_thread(analyze_bias, req.text[:1000])

@app.get("/bias/keywords")
def bias_keywords():
    return KEYWORD_CATEGORIES

@app.get("/status")
def status():
    return {
        "cached_articles": len(NEWS_CACHE),
        "tickers_cached":  len(_CACHE),
        "last_updated":    LAST_UPDATED,
        "status":          "ok" if NEWS_CACHE else "warming_up",
    }