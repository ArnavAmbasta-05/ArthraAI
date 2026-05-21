import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
TEST_CSV   = BASE_DIR / "test.csv"
MODEL_ROOT = BASE_DIR / "local-model"
FINBERT_PATH = MODEL_ROOT / "finbert"
FLANL_PATH   = MODEL_ROOT / "flan-t5"

LABEL_MAP = {0: "Bearish", 1: "Neutral", 2: "Bullish"}
LABEL_REV = {"Bearish": 0, "Neutral": 1, "Bullish": 2}

try:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoModelForSeq2SeqLM,
    )
    from sklearn.metrics import ( # type: ignore
        accuracy_score,
        f1_score,
        classification_report,
        confusion_matrix,
    )
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

# Import keyword engine from ai.py
sys.path.insert(0, str(BASE_DIR / "backend"))
try:
    from ai import score_bias
    HAS_KW = True
except ImportError:
    HAS_KW = False
    print("⚠️  ai.py not importable — skipping keyword comparison")


# ══════════════════════════════════════════════════════════
# FINBERT EVALUATION
# ══════════════════════════════════════════════════════════

def evaluate_finbert(test_df: pd.DataFrame):
    print("\n" + "═" * 60)
    print("  FinBERT Classifier Evaluation")
    print("═" * 60)

    if not FINBERT_PATH.exists():
        print(f"  ❌ {FINBERT_PATH} not found — run train_model.py first")
        return

    device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(FINBERT_PATH))
    model     = AutoModelForSequenceClassification.from_pretrained(
        str(FINBERT_PATH)
    ).to(device).eval()

    texts  = test_df["text"].tolist()
    y_true = test_df["label_id"].tolist()
    y_pred = []
    probs  = []

    BATCH = 32
    print(f"  Running inference on {len(texts)} examples (batch={BATCH})...")

    with torch.no_grad():
        for i in range(0, len(texts), BATCH):
            batch = texts[i:i+BATCH]
            enc   = tokenizer(
                batch,
                truncation=True,
                max_length=128,
                padding=True,
                return_tensors="pt",
            ).to(device)
            out   = model(**enc)
            logits = out.logits.cpu().numpy()
            preds  = np.argmax(logits, axis=-1).tolist()
            soft   = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
            y_pred.extend(preds)
            probs.extend(soft.tolist())

    # ── Metrics ───────────────────────────────────────────
    acc = accuracy_score(y_true, y_pred)
    f1  = f1_score(y_true, y_pred, average="macro", zero_division=0)

    print(f"\n  Overall Accuracy : {acc:.4f}  ({acc*100:.1f}%)")
    print(f"  Macro F1 Score   : {f1:.4f}")
    print()
    print("  Per-class F1:")
    report = classification_report(
        y_true, y_pred,
        target_names=["Bearish", "Neutral", "Bullish"],
        zero_division=0,
    )
    for line in report.split("\n"):
        print(f"    {line}")

    # ── Confusion matrix ──────────────────────────────────
    cm = confusion_matrix(y_true, y_pred)
    print("\n  Confusion matrix (rows=true, cols=pred):")
    print(f"  {'':12} {'Bearish':>8} {'Neutral':>8} {'Bullish':>8}")
    for i, row_name in enumerate(["Bearish", "Neutral", "Bullish"]):
        print(f"  {row_name:12} {cm[i][0]:>8} {cm[i][1]:>8} {cm[i][2]:>8}")

    # ── Worst confidence examples ─────────────────────────
    print("\n  Lowest-confidence correct predictions (model uncertainty):")
    for idx, (true, pred, prob) in enumerate(zip(y_true, y_pred, probs)):
        if true == pred:
            conf = prob[pred]
            if conf < 0.65:
                text = texts[idx][:80]
                print(f"    [{LABEL_MAP[pred]:7}] conf={conf:.2f} | {text}")

    # ── FinBERT vs keyword disagreements ──────────────────
    if HAS_KW:
        print("\n  FinBERT vs Keyword engine disagreements:")
        n_disagree = 0
        for idx, (true, pred) in enumerate(zip(y_true, y_pred)):
            kw     = score_bias(texts[idx])
            kw_lbl = LABEL_REV.get(kw["label"], 1)
            if pred != kw_lbl and n_disagree < 10:
                n_disagree += 1
                text = texts[idx][:70]
                print(f"    True={LABEL_MAP[true]:7} | FinBERT={LABEL_MAP[pred]:7} | KW={kw['label']:7} | {text}")
        if n_disagree == 0:
            print("    None in test set — models are well-aligned")

    return {"accuracy": acc, "f1_macro": f1}


# ══════════════════════════════════════════════════════════
# FLAN-T5 SUMMARY QUALITY CHECK
# ══════════════════════════════════════════════════════════

def evaluate_flan_t5(test_df: pd.DataFrame, n_samples: int = 5):
    print("\n" + "═" * 60)
    print("  flan-t5-base Summarisation Quality Check")
    print("═" * 60)

    if not FLANL_PATH.exists():
        print(f"  ❌ {FLANL_PATH} not found — run train_model.py first")
        return

    device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(FLANL_PATH))
    model     = AutoModelForSeq2SeqLM.from_pretrained(
        str(FLANL_PATH)
    ).to(device).eval()

    samples = test_df.sample(min(n_samples, len(test_df)), random_state=42)
    print(f"  Generating summaries for {len(samples)} samples...\n")

    with torch.no_grad():
        for _, row in samples.iterrows():
            prompt = f"summarize financial news: {row['text']}"
            enc    = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=256,
            ).to(device)
            out = model.generate(
                **enc,
                max_new_tokens=80,
                num_beams=4,
                no_repeat_ngram_size=2,
                early_stopping=True,
            )
            summary = tokenizer.decode(out[0], skip_special_tokens=True)
            print(f"  [{row['label']:7}]")
            print(f"  Input  : {row['text'][:90]}")
            print(f"  Summary: {summary}")
            print()


# ══════════════════════════════════════════════════════════
# HYBRID SCORE VALIDATION
# ══════════════════════════════════════════════════════════

def validate_hybrid_scores(test_df: pd.DataFrame):
    """
    Simulate the hybrid 60% FinBERT + 40% keyword score
    and show how it compares to ground-truth bias_score.
    """
    if not HAS_KW or not FINBERT_PATH.exists():
        return

    print("\n" + "═" * 60)
    print("  Hybrid Score Validation (FinBERT 60% + Keywords 40%)")
    print("═" * 60)

    device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(FINBERT_PATH))
    model     = AutoModelForSequenceClassification.from_pretrained(
        str(FINBERT_PATH)
    ).to(device).eval()

    samples     = test_df.sample(min(20, len(test_df)), random_state=1).reset_index()
    errors      = []

    with torch.no_grad():
        for _, row in samples.iterrows():
            enc    = tokenizer(
                row["text"],
                truncation=True, max_length=128,
                return_tensors="pt",
            ).to(device)
            out    = model(**enc)
            logits = out.logits.cpu().numpy()[0]
            soft   = np.exp(logits) / np.exp(logits).sum()
            # FinBERT: Bearish(0)→0, Neutral(1)→50, Bullish(2)→100
            finbert_score = float(soft[0] * 0 + soft[1] * 50 + soft[2] * 100)

            kw            = score_bias(row["text"])
            kw_score      = kw["score"]
            hybrid        = 0.6 * finbert_score + 0.4 * kw_score
            true_score    = row["bias_score"]
            error         = abs(hybrid - true_score)
            errors.append(error)

    mae = np.mean(errors)
    print(f"  Mean Absolute Error (hybrid vs ground truth): {mae:.1f} points")
    print(f"  Max error: {max(errors):.1f} | Min error: {min(errors):.1f}")
    if mae < 10:
        print("  ✅ Excellent hybrid scoring accuracy")
    elif mae < 15:
        print("  ✅ Good hybrid scoring accuracy")
    else:
        print("  ⚠️  High error — consider retraining with more epochs")


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not TEST_CSV.exists():
        print(f"❌ {TEST_CSV} not found — run build_dataset.py first")
        sys.exit(1)

    test_df = pd.read_csv(TEST_CSV)
    print(f"Loaded test set: {len(test_df)} examples")
    print(f"Label distribution: {dict(test_df['label'].value_counts())}")

    evaluate_finbert(test_df)
    evaluate_flan_t5(test_df)
    validate_hybrid_scores(test_df)

    print("\n🎉 Evaluation complete.")