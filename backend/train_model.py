import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR
MODEL_ROOT  = BASE_DIR / "local-model"
FINBERT_OUT = MODEL_ROOT / "finbert"
FLANL_OUT   = MODEL_ROOT / "flan-t5"

TRAIN_CSV = DATA_DIR / "train.csv"
VAL_CSV   = DATA_DIR / "val.csv"
SUMM_CSV  = DATA_DIR / "summarisation.csv"

LABEL_MAP = {0: "Bearish", 1: "Neutral", 2: "Bullish"}

# ─── Imports (deferred so import error is clear) ──────────
try:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoModelForSeq2SeqLM,
        Trainer,
        TrainingArguments,
        DataCollatorWithPadding,
        DataCollatorForSeq2Seq,
        EarlyStoppingCallback,
    )
    from datasets import Dataset # type: ignore
    from sklearn.metrics import ( # type: ignore
        accuracy_score,
        f1_score,
        classification_report,
    )
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install transformers datasets torch scikit-learn pandas numpy")
    sys.exit(1)


# ══════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════

def load_splits():
    """Load and validate train / val CSVs."""
    for p in (TRAIN_CSV, VAL_CSV):
        if not p.exists():
            print(f"❌ {p} not found — run build_dataset.py first")
            sys.exit(1)

    train_df = pd.read_csv(TRAIN_CSV)
    val_df   = pd.read_csv(VAL_CSV)

    # Validate required columns
    for col in ("text", "label", "label_id"):
        assert col in train_df.columns, f"Missing column '{col}' in train.csv"

    print(f"  train: {len(train_df)} rows | val: {len(val_df)} rows")
    print(f"  label distribution (train): {dict(train_df['label'].value_counts())}")
    return train_df, val_df


def compute_metrics_cls(eval_pred):
    """Compute accuracy + macro F1 for classification."""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc   = accuracy_score(labels, preds)
    f1    = f1_score(labels, preds, average="macro", zero_division=0)
    return {"accuracy": acc, "f1_macro": f1}


# ══════════════════════════════════════════════════════════
# MODEL 1 — FinBERT FINE-TUNING (Classification)
# ══════════════════════════════════════════════════════════

def train_finbert():
    print("\n" + "═" * 60)
    print("  MODEL 1 — FinBERT Sentiment Classifier")
    print("═" * 60)

    model_name = "ProsusAI/finbert"
    local_base = MODEL_ROOT / "finbert-base"

    # Load from local if available, otherwise from HuggingFace
    src = str(local_base) if local_base.exists() else model_name
    print(f"  Loading from: {src}")

    tokenizer = AutoTokenizer.from_pretrained(src)
    model     = AutoModelForSequenceClassification.from_pretrained(
        src,
        num_labels=3,
        id2label=LABEL_MAP,
        label2id={v: k for k, v in LABEL_MAP.items()},
        ignore_mismatched_sizes=True,  # safe when changing num_labels
    )

    train_df, val_df = load_splits()

    # ── Tokenise ──────────────────────────────────────────
    def tokenise(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=128,        # financial headlines rarely exceed 128 tokens
        )

    train_ds = Dataset.from_pandas(train_df[["text", "label_id"]].rename(
        columns={"label_id": "labels"}
    ))
    val_ds = Dataset.from_pandas(val_df[["text", "label_id"]].rename(
        columns={"label_id": "labels"}
    ))

    train_ds = train_ds.map(tokenise, batched=True, remove_columns=["text"])
    val_ds   = val_ds.map(tokenise, batched=True, remove_columns=["text"])

    collator = DataCollatorWithPadding(tokenizer)

    # ── Training args ─────────────────────────────────────
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16  = device == "cuda"
    print(f"  Device: {device} | fp16: {use_fp16}")

    args = TrainingArguments(
        output_dir                  = str(FINBERT_OUT),
        num_train_epochs            = 5,
        per_device_train_batch_size = 16,
        per_device_eval_batch_size  = 32,
        learning_rate               = 2e-5,
        weight_decay                = 0.01,
        warmup_ratio                = 0.1,
        lr_scheduler_type           = "cosine",
        eval_strategy               = "epoch",
        save_strategy               = "epoch",
        load_best_model_at_end      = True,
        metric_for_best_model       = "f1_macro",
        greater_is_better           = True,
        fp16                        = use_fp16,
        dataloader_num_workers      = 0,       # safe on Windows
        logging_dir                 = str(BASE_DIR / "logs" / "finbert"),
        logging_steps               = 50,
        report_to                   = "none",  # no wandb
        save_total_limit            = 2,
        seed                        = 42,
    )

    trainer = Trainer(
        model           = model,
        args            = args,
        train_dataset   = train_ds,
        eval_dataset    = val_ds,
        tokenizer       = tokenizer,
        data_collator   = collator,
        compute_metrics = compute_metrics_cls,
        callbacks       = [EarlyStoppingCallback(early_stopping_patience=2)],
    )

    print("  Starting FinBERT training...")
    trainer.train()

    # Save best model
    FINBERT_OUT.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(FINBERT_OUT))
    tokenizer.save_pretrained(str(FINBERT_OUT))

    # Final eval
    metrics = trainer.evaluate()
    print(f"\n  ✅ FinBERT training complete")
    print(f"     Val accuracy : {metrics.get('eval_accuracy', 0):.4f}")
    print(f"     Val F1 macro : {metrics.get('eval_f1_macro', 0):.4f}")
    print(f"     Saved to     : {FINBERT_OUT}")

    return metrics


# ══════════════════════════════════════════════════════════
# MODEL 2 — FLAN-T5-BASE FINE-TUNING (Summarisation)
# ══════════════════════════════════════════════════════════

def train_flan_t5():
    print("\n" + "═" * 60)
    print("  MODEL 2 — flan-t5-base Summarisation")
    print("═" * 60)

    if not SUMM_CSV.exists():
        print(f"  ❌ {SUMM_CSV} not found — run build_dataset.py first")
        return

    summ_df = pd.read_csv(SUMM_CSV).dropna(subset=["input", "target"])
    print(f"  Summarisation examples: {len(summ_df)}")

    model_name = "google/flan-t5-base"
    local_base = MODEL_ROOT / "flan-t5-base"
    src        = str(local_base) if local_base.exists() else model_name
    print(f"  Loading from: {src}")

    tokenizer = AutoTokenizer.from_pretrained(src)
    model     = AutoModelForSeq2SeqLM.from_pretrained(src)

    # ── Tokenise ──────────────────────────────────────────
    MAX_IN  = 256
    MAX_OUT = 128

    def tokenise_summ(batch):
        model_inputs = tokenizer(
            batch["input"],
            max_length=MAX_IN,
            truncation=True,
        )
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(
                batch["target"],
                max_length=MAX_OUT,
                truncation=True,
            )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    n_val    = max(100, int(len(summ_df) * 0.10))
    train_s  = Dataset.from_pandas(summ_df.iloc[:-n_val][["input", "target"]])
    val_s    = Dataset.from_pandas(summ_df.iloc[-n_val:][["input", "target"]])

    train_s  = train_s.map(tokenise_summ, batched=True, remove_columns=["input", "target"])
    val_s    = val_s.map(tokenise_summ,   batched=True, remove_columns=["input", "target"])

    collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

    device   = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = device == "cuda"

    args = TrainingArguments(
        output_dir                  = str(FLANL_OUT),
        num_train_epochs            = 3,
        per_device_train_batch_size = 8,
        per_device_eval_batch_size  = 16,
        learning_rate               = 3e-5,
        weight_decay                = 0.01,
        warmup_ratio                = 0.05,
        eval_strategy               = "epoch",
        save_strategy               = "epoch",
        load_best_model_at_end      = True,
        metric_for_best_model       = "eval_loss",
        greater_is_better           = False,
        fp16                        = use_fp16,
        dataloader_num_workers      = 0,
        logging_dir                 = str(BASE_DIR / "logs" / "flan-t5"),
        logging_steps               = 50,
        report_to                   = "none",
        save_total_limit            = 2,
        seed                        = 42,
    )

    trainer = Trainer(
        model         = model,
        args          = args,
        train_dataset = train_s,
        eval_dataset  = val_s,
        tokenizer     = tokenizer,
        data_collator = collator,
    )

    print("  Starting flan-t5-base training...")
    trainer.train()

    FLANL_OUT.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(FLANL_OUT))
    tokenizer.save_pretrained(str(FLANL_OUT))

    metrics = trainer.evaluate()
    print(f"\n  ✅ flan-t5-base training complete")
    print(f"     Val loss : {metrics.get('eval_loss', 0):.4f}")
    print(f"     Saved to : {FLANL_OUT}")


# ══════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["finbert", "flan-t5", "both"],
        default="both",
        help="Which model to train (default: both)",
    )
    args = parser.parse_args()

    print("ArthraAI Model Training Pipeline")
    print(f"Base dir  : {BASE_DIR}")
    print(f"Model out : {MODEL_ROOT}")
    print(f"Training  : {args.model}")

    if args.model in ("finbert", "both"):
        train_finbert()

    if args.model in ("flan-t5", "both"):
        train_flan_t5()

    print("\n🎉 Training complete. Run evaluate_model.py to validate.")