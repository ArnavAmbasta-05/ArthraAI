import sys
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
MODEL_ROOT = BASE_DIR / "local-model"

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoModelForSeq2SeqLM,
    )
except ImportError:
    print("❌ transformers not installed.")
    print("   Run: pip install transformers torch safetensors sentencepiece")
    sys.exit(1)

MODELS = [
    {
        "name":       "ProsusAI/finbert",
        "save_path":  MODEL_ROOT / "finbert-base",
        "cls":        AutoModelForSequenceClassification,
        "label":      "FinBERT (sentiment classifier)",
        "kwargs":     {"num_labels": 3, "ignore_mismatched_sizes": True},
    },
    {
        "name":       "google/flan-t5-base",
        "save_path":  MODEL_ROOT / "flan-t5-base",
        "cls":        AutoModelForSeq2SeqLM,
        "label":      "flan-t5-base (summarisation)",
        "kwargs":     {},
    },
]


def download():
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)

    for m in MODELS:
        save_path = m["save_path"]

        if save_path.exists() and any(save_path.iterdir()):
            print(f"⏭  {m['label']} already at {save_path} — skipping")
            continue

        print(f"\n⬇️  Downloading {m['label']}")
        print(f"   Source: {m['name']}  →  {save_path}")
        save_path.mkdir(parents=True, exist_ok=True)

        print("   Fetching tokenizer...")
        tok = AutoTokenizer.from_pretrained(m["name"])
        tok.save_pretrained(str(save_path))

        print("   Fetching model weights...")
        model = m["cls"].from_pretrained(m["name"], **m["kwargs"])
        model.save_pretrained(str(save_path))

        print(f"   ✅ Saved to {save_path}")

    print("\n✅ All models downloaded.")
    print("\nNext steps:")
    print("  python build_dataset.py   — generate training data")
    print("  python train_model.py     — fine-tune both models")
    print("  python evaluate_model.py  — validate on test set")


if __name__ == "__main__":
    download()