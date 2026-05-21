"""
runner.py — standalone pipeline runner for debugging outside FastAPI.
Run from project root: python runner.py
"""
import time
from sources import fetch_all_news
from ai import process_news

INTERVAL = 300  # seconds between cycles


def run_pipeline():
    print("🚀 Runner started\n")

    while True:
        try:
            print("📥 Fetching news...")
            articles = fetch_all_news()
            print(f"📰 {len(articles)} articles fetched\n")

            print("🧠 Processing articles...\n")

            for article in articles:
                result = process_news(article.get("summary", ""))

                print("=" * 50)
                print(f"📰 TITLE:   {article['title']}")
                print(f"🏢 SOURCE:  {article['source']}")
                print(f"📊 LABEL:   {result['label']}  (bias {result['bias']}%)")
                print(f"💡 INSIGHT: {result['insight']}")
                print(f"🧾 SUMMARY: {result['summary'][:120]}")
                print("=" * 50 + "\n")

            print("✅ Cycle complete")

        except Exception as e:
            print(f"❌ Pipeline error: {e}")

        print(f"\n⏳ Sleeping {INTERVAL}s...\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_pipeline()