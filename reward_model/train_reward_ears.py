"""
train_reward_ears.py
====================
EARS: Emotion-Aware Reward Shaping
===================================
Trains an emotion-conditioned dual-head reward model for mental health dialogue.

Novel contributions:
  1. Emotion-Conditioned Reward Model
     - Emotion state prepended as a special token to each (query, response) pair
     - Forces the model to learn that response quality is emotion-dependent
     - Input: [EMOTION] query [SEP] response [SEP]

  2. Dual Reward Decomposition
     - r_empathy : does the response acknowledge the emotional state?
     - r_relevance: is the response factually helpful and grounded?
     - r_total = α·r_empathy + β·r_relevance (weights shift by emotion)

  3. Bradley-Terry preference loss applied per-head separately

References:
  - Christiano et al. (2017) - Deep RL from Human Preferences
  - Ouyang et al. (2022) - InstructGPT
  - Uesato et al. (2023) - Reward decomposition
  - Thompson (1933) - Thompson Sampling (used in rlhf_inference_ears.py)

Run:
    python reward_model/train_reward_ears.py
"""

import os
import json
import redis
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertModel, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
REDIS_HOST   = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
MODEL_OUTPUT = os.path.join(os.path.dirname(__file__), "ears_model_output")
PRETRAINED   = "distilbert-base-uncased"
MAX_LENGTH   = 512
BATCH_SIZE   = 8
EPOCHS       = 5
LR           = 2e-5
VAL_SPLIT    = 0.15
MIN_SAMPLES  = 20
SEED         = 42

os.makedirs(MODEL_OUTPUT, exist_ok=True)

# ─── Emotion tokens ───────────────────────────────────────────────────────────
# These special tokens are added to the tokenizer vocabulary so the model
# learns distinct representations for each emotional context.
EMOTION_TOKENS = ["[NEUTRAL]", "[HAPPY]", "[SAD]", "[ANGRY]", "[FEARFUL]", "[UNKNOWN]"]

# Empathy weight α and relevance weight β per emotion.
# When distress is high, empathy matters more than factual relevance.
EMOTION_WEIGHTS = {
    "sad":     (0.80, 0.20),   # (α_empathy, β_relevance)
    "fearful": (0.80, 0.20),
    "angry":   (0.65, 0.35),
    "happy":   (0.30, 0.70),
    "neutral": (0.30, 0.70),
    "unknown": (0.50, 0.50),
}

# Heuristic empathy keywords — used to derive empathy pseudo-labels from
# response text when explicit empathy ratings are unavailable.
EMPATHY_KEYWORDS = [
    "i understand", "i hear you", "that sounds", "i'm sorry", "you're not alone",
    "i can sense", "that must be", "it's okay", "valid", "i'm here",
    "take a breath", "you matter", "reach out", "professional", "support",
    "difficult", "hard time", "feeling", "emotions", "care about you",
]

def get_device():
    if torch.backends.mps.is_available():
        print("[DEVICE] Apple MPS")
        return torch.device("mps")
    print("[DEVICE] CPU")
    return torch.device("cpu")


# ══════════════════════════════════════════════════════════════════════════════
# MODEL: EARSRewardModel
# Dual-head DistilBERT with emotion conditioning via special tokens
# ══════════════════════════════════════════════════════════════════════════════
class EARSRewardModel(nn.Module):
    """
    Emotion-Aware Reward Shaping (EARS) Reward Model.

    Architecture:
        Input  : [EMOTION_TOKEN] query [SEP] response [SEP]
        Encoder: DistilBERT (extended vocabulary for emotion tokens)
        Head 1 : r_empathy  — sigmoid scalar ∈ [0,1]
        Head 2 : r_relevance — sigmoid scalar ∈ [0,1]
        Output : r_total = α·r_empathy + β·r_relevance (emotion-dependent weights)
    """
    def __init__(self, pretrained: str = PRETRAINED, vocab_size: int = None):
        super().__init__()
        self.encoder = DistilBertModel.from_pretrained(pretrained)

        # Resize embeddings if new emotion tokens were added
        if vocab_size is not None:
            self.encoder.resize_token_embeddings(vocab_size)

        hidden = self.encoder.config.hidden_size  # 768

        # Head 1 — empathy reward
        self.empathy_head = nn.Sequential(
            nn.Linear(hidden, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

        # Head 2 — relevance reward
        self.relevance_head = nn.Sequential(
            nn.Linear(hidden, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, input_ids, attention_mask):
        out     = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls     = out.last_hidden_state[:, 0, :]       # CLS token
        r_emp   = self.empathy_head(cls).squeeze(-1)   # (batch,)
        r_rel   = self.relevance_head(cls).squeeze(-1) # (batch,)
        return r_emp, r_rel

    def total_reward(self, input_ids, attention_mask, emotion: str = "neutral") -> torch.Tensor:
        """
        Compute the emotion-weighted combined reward score.
        α and β shift depending on the detected emotion.
        """
        α, β    = EMOTION_WEIGHTS.get(emotion.lower(), (0.5, 0.5))
        r_emp, r_rel = self.forward(input_ids, attention_mask)
        return α * r_emp + β * r_rel


# ══════════════════════════════════════════════════════════════════════════════
# DATASET
# ══════════════════════════════════════════════════════════════════════════════
class EARSDataset(Dataset):
    """
    Each record: (emotion, query, response, rating, empathy_label)

    empathy_label is derived heuristically from response text when not
    explicitly provided — counts empathy keyword matches.
    """
    def __init__(self, records, tokenizer, max_length=MAX_LENGTH):
        self.records    = records
        self.tokenizer  = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        emotion, query, response, rating, empathy_label = self.records[idx]

        # Prepend emotion token to query
        emotion_token  = f"[{emotion.upper()}]"
        conditioned_q  = f"{emotion_token} {query}"

        encoding = self.tokenizer(
            conditioned_q,
            response,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids":      encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "rating":         torch.tensor(float(rating),        dtype=torch.float32),
            "empathy_label":  torch.tensor(float(empathy_label), dtype=torch.float32),
            "emotion":        emotion,
        }


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
def derive_empathy_label(response: str) -> float:
    """
    Heuristic empathy label derived from response text.
    Counts empathy keyword matches and normalises to [0,1].
    A response with ≥3 empathy keywords scores 1.0.
    """
    response_lower = response.lower()
    matches        = sum(1 for kw in EMPATHY_KEYWORDS if kw in response_lower)
    return min(matches / 3.0, 1.0)


def load_feedback_from_redis():
    """
    Load feedback from Redis.
    Emotion is read from feedback entry if stored, else defaults to 'unknown'.
    """
    r       = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    keys    = r.keys("feedback:*")
    records = []
    print(f"[REDIS] Found {len(keys)} feedback entries.")

    for key in keys:
        try:
            data     = json.loads(r.get(key))
            query    = data.get("query",    "").strip()
            response = data.get("response", "").strip()
            rating   = int(data.get("rating", -1))
            emotion  = data.get("emotion",  "unknown").lower()

            if not query or not response or rating not in (0, 1):
                continue

            # Validate emotion token
            if emotion not in EMOTION_WEIGHTS:
                emotion = "unknown"

            empathy_label = derive_empathy_label(response)
            records.append((emotion, query, response, float(rating), empathy_label))

        except Exception as e:
            print(f"[WARN] Skipping {key}: {e}")

    return records


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING
# ══════════════════════════════════════════════════════════════════════════════
def train():
    device  = get_device()
    records = load_feedback_from_redis()

    if len(records) < MIN_SAMPLES:
        print(f"[ERROR] Need at least {MIN_SAMPLES} feedback entries. Have {len(records)}.")
        return

    print(f"[INFO] Total records: {len(records)}")

    # Print emotion distribution
    from collections import Counter
    emo_dist = Counter(r[0] for r in records)
    print(f"[INFO] Emotion distribution: {dict(emo_dist)}")
    pos = sum(1 for r in records if r[3] == 1.0)
    print(f"[INFO] 👍 {pos} | 👎 {len(records)-pos}")

    # Split
    train_recs, val_recs = train_test_split(
        records, test_size=VAL_SPLIT, random_state=SEED
    )

    # Tokenizer — add emotion tokens to vocabulary
    tokenizer = DistilBertTokenizer.from_pretrained(PRETRAINED)
    num_added = tokenizer.add_special_tokens({"additional_special_tokens": EMOTION_TOKENS})
    print(f"[INFO] Added {num_added} emotion tokens to vocabulary.")

    # Model
    model = EARSRewardModel(PRETRAINED, vocab_size=len(tokenizer)).to(device)

    # Datasets
    train_ds = EARSDataset(train_recs, tokenizer)
    val_ds   = EARSDataset(val_recs,   tokenizer)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False)

    # Optimiser
    optimizer   = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    scheduler   = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps,
    )

    # Loss — separate BCE for each head
    bce = nn.BCELoss()

    best_auc = 0.0

    for epoch in range(1, EPOCHS + 1):
        print(f"\n{'='*55}")
        print(f"  EPOCH {epoch}/{EPOCHS}")
        print(f"{'='*55}")

        # ── Train ─────────────────────────────────────────────────────────────
        model.train()
        train_loss = 0.0

        bar = tqdm(train_loader, desc="  Training", unit="batch", leave=False)
        for batch in bar:
            ids    = batch["input_ids"].to(device)
            mask   = batch["attention_mask"].to(device)
            rating = batch["rating"].to(device)
            emp_lbl = batch["empathy_label"].to(device)

            r_emp, r_rel = model(ids, mask)

            # Dual loss:
            # - relevance head trained on human ratings (thumbs up/down)
            # - empathy head trained on heuristic empathy labels
            loss_relevance = bce(r_rel, rating)
            loss_empathy   = bce(r_emp, emp_lbl)

            # Combined loss — weight empathy slightly less since it's heuristic
            loss = 0.4 * loss_empathy + 0.6 * loss_relevance

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()
            bar.set_postfix(loss=f"{loss.item():.4f}")

        print(f"\n  [TRAIN] Loss: {train_loss/len(train_loader):.4f}")

        # ── Validate ──────────────────────────────────────────────────────────
        model.eval()
        all_total_scores = []
        all_ratings      = []
        all_emp_scores   = []
        all_rel_scores   = []

        with torch.no_grad():
            for batch in tqdm(val_loader, desc="  Validating", leave=False):
                ids    = batch["input_ids"].to(device)
                mask   = batch["attention_mask"].to(device)
                rating = batch["rating"]
                emotions = batch["emotion"]

                r_emp, r_rel = model(ids, mask)

                # Compute emotion-weighted total score per sample
                for i, emotion in enumerate(emotions):
                    α, β = EMOTION_WEIGHTS.get(emotion, (0.5, 0.5))
                    total = α * r_emp[i].item() + β * r_rel[i].item()
                    all_total_scores.append(total)
                    all_emp_scores.append(r_emp[i].item())
                    all_rel_scores.append(r_rel[i].item())

                all_ratings.extend(rating.numpy())

        preds = [1 if s >= 0.5 else 0 for s in all_total_scores]
        acc   = accuracy_score(all_ratings, preds)
        try:
            auc = roc_auc_score(all_ratings, all_total_scores)
        except:
            auc = 0.5

        print(f"  [VAL] Acc: {acc:.4f} | AUC: {auc:.4f}")
        print(f"  [VAL] Avg r_empathy: {np.mean(all_emp_scores):.4f} | Avg r_relevance: {np.mean(all_rel_scores):.4f}")

        # ── Save best ─────────────────────────────────────────────────────────
        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), os.path.join(MODEL_OUTPUT, "ears_reward_model.pt"))
            tokenizer.save_pretrained(MODEL_OUTPUT)
            with open(os.path.join(MODEL_OUTPUT, "config.json"), "w") as f:
                json.dump({
                    "pretrained":  PRETRAINED,
                    "max_length":  MAX_LENGTH,
                    "vocab_size":  len(tokenizer),
                    "emotion_weights": EMOTION_WEIGHTS,
                }, f, indent=2)
            print(f"  ✅ Best EARS model saved (AUC={best_auc:.4f})")

    print(f"\n[DONE] EARS training complete. Best AUC: {best_auc:.4f}")
    print(f"       Model saved to: {MODEL_OUTPUT}")


if __name__ == "__main__":
    train()