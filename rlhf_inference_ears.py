"""
rlhf_inference_ears.py
=======================
EARS: Emotion-Aware Reward Shaping — Inference Module
======================================================

Implements:
  1. Emotion-conditioned reward scoring
     - Prepends emotion token to query before scoring
     - Reward heads weighted by detected emotion (α·r_empathy + β·r_relevance)

  2. Thompson Sampling for candidate selection
     - Replaces deterministic argmax (Best-of-N)
     - Maintains Beta distribution posteriors over each candidate's reward
     - Samples from posterior to balance exploration vs exploitation
     - Early stage (few feedback): high uncertainty → more exploration
     - Later stage (many feedback): low uncertainty → exploits best candidate

  3. Graceful fallback
     - If EARS model not trained: falls back to standard single response

Thompson Sampling reference:
    Thompson, W.R. (1933). On the likelihood that one unknown probability
    exceeds another in view of the evidence of two samples.
    Biometrika, 25(3/4), 285–294.

Reward decomposition reference:
    Uesato, J. et al. (2023). Solving math word problems with process-
    and outcome-based feedback. arXiv:2211.14275.
"""

import os
import json
import torch
import torch.nn as nn
import numpy as np
from transformers import DistilBertTokenizer, DistilBertModel

# Path to EARS trained model
EARS_MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "reward_model", "ears_model_output"
)

# Emotion weights — must match train_reward_ears.py
EMOTION_WEIGHTS = {
    "sad":     (0.80, 0.20),
    "fearful": (0.80, 0.20),
    "angry":   (0.65, 0.35),
    "happy":   (0.30, 0.70),
    "neutral": (0.30, 0.70),
    "unknown": (0.50, 0.50),
}


# ══════════════════════════════════════════════════════════════════════════════
# MODEL (must match train_reward_ears.py exactly)
# ══════════════════════════════════════════════════════════════════════════════
class EARSRewardModel(nn.Module):
    def __init__(self, pretrained: str = "distilbert-base-uncased", vocab_size: int = None):
        super().__init__()
        self.encoder = DistilBertModel.from_pretrained(pretrained)
        if vocab_size is not None:
            self.encoder.resize_token_embeddings(vocab_size)
        hidden = self.encoder.config.hidden_size

        self.empathy_head = nn.Sequential(
            nn.Linear(hidden, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 1), nn.Sigmoid(),
        )
        self.relevance_head = nn.Sequential(
            nn.Linear(hidden, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 1), nn.Sigmoid(),
        )

    def forward(self, input_ids, attention_mask):
        out   = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls   = out.last_hidden_state[:, 0, :]
        r_emp = self.empathy_head(cls).squeeze(-1)
        r_rel = self.relevance_head(cls).squeeze(-1)
        return r_emp, r_rel


# ══════════════════════════════════════════════════════════════════════════════
# THOMPSON SAMPLING
# ══════════════════════════════════════════════════════════════════════════════
class ThompsonSampler:
    """
    Beta-distribution Thompson Sampler for candidate selection.

    Each candidate maintains a Beta(α, β) posterior over its reward.
    - α (successes) = accumulated reward scores above 0.5
    - β (failures)  = accumulated reward scores below 0.5

    At selection time, we sample from each candidate's posterior and
    pick the candidate with the highest sample. This naturally balances:
    - Exploration when uncertainty is high (α and β are small)
    - Exploitation when uncertainty is low (α and β are large)

    For a single-turn selection (no history), we initialise with
    prior Beta(1, 1) — uniform — and update with the current reward scores.
    """

    def __init__(self, n_candidates: int, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.n = n_candidates
        # Initialise Beta priors — Beta(1,1) = uniform over [0,1]
        self.alphas = np.ones(n_candidates) * prior_alpha
        self.betas  = np.ones(n_candidates) * prior_beta

    def update(self, scores: list):
        """
        Update Beta posteriors with observed reward scores.
        Score > 0.5 → increments α (success); ≤ 0.5 → increments β (failure).
        """
        for i, score in enumerate(scores):
            if score > 0.5:
                self.alphas[i] += score          # weight by magnitude
            else:
                self.betas[i]  += (1.0 - score)  # weight by failure magnitude

    def sample(self) -> int:
        """
        Sample from each Beta posterior and return the index of the winner.
        This is the core Thompson Sampling step.
        """
        samples = np.random.beta(self.alphas, self.betas)
        return int(np.argmax(samples))

    def get_uncertainty(self) -> list:
        """
        Return uncertainty estimate for each candidate.
        Variance of Beta(α,β) = αβ / ((α+β)²(α+β+1))
        Higher variance = more uncertain.
        """
        uncertainties = []
        for i in range(self.n):
            a, b = self.alphas[i], self.betas[i]
            var  = (a * b) / ((a + b) ** 2 * (a + b + 1))
            uncertainties.append(var)
        return uncertainties


# ══════════════════════════════════════════════════════════════════════════════
# EARS RANKER
# ══════════════════════════════════════════════════════════════════════════════
class EARSRanker:
    """
    Main EARS inference class.

    Usage:
        ranker = EARSRanker()

        # In voice_chat / chat routes:
        best_response, metadata = ranker.select(
            query     = "I feel really sad today",
            candidates = [c1, c2, c3],
            emotion   = "sad",          # from SER model
        )
        print(metadata)
        # {
        #   'selected_idx': 2,
        #   'r_empathy':    [0.81, 0.62, 0.89],
        #   'r_relevance':  [0.54, 0.71, 0.68],
        #   'total_scores': [0.75, 0.63, 0.85],
        #   'ts_samples':   [0.74, 0.61, 0.88],
        #   'uncertainties':[0.02, 0.03, 0.01],
        #   'alpha': 0.8, 'beta': 0.2,
        #   'emotion': 'sad',
        #   'method': 'EARS-Thompson'
        # }
    """

    def __init__(self, model_dir: str = EARS_MODEL_DIR):
        self.model     = None
        self.tokenizer = None
        self.max_len   = 512
        self.device    = self._get_device()
        self._load(model_dir)

    def _get_device(self):
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load(self, model_dir: str):
        pt_path  = os.path.join(model_dir, "ears_reward_model.pt")
        cfg_path = os.path.join(model_dir, "config.json")

        if not os.path.exists(pt_path):
            print(f"[EARS] No model at {model_dir}. Will use fallback (first candidate).")
            return

        try:
            with open(cfg_path) as f:
                cfg = json.load(f)

            self.max_len   = cfg.get("max_length", 512)
            vocab_size     = cfg.get("vocab_size", None)
            pretrained     = cfg.get("pretrained", "distilbert-base-uncased")

            self.tokenizer = DistilBertTokenizer.from_pretrained(model_dir)
            ears           = EARSRewardModel(pretrained, vocab_size=vocab_size)
            ears.load_state_dict(torch.load(pt_path, map_location=self.device))
            ears.eval()
            ears.to(self.device)
            self.model = ears
            print(f"[EARS] Model loaded from {model_dir}")
        except Exception as e:
            print(f"[EARS] Load failed: {e}. Using fallback.")

    def is_ready(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def _score_candidate(self, query: str, response: str, emotion: str) -> tuple:
        """
        Score one (query, response) pair with emotion conditioning.
        Returns (r_empathy, r_relevance, r_total).
        """
        emotion_token = f"[{emotion.upper()}]"
        conditioned_q = f"{emotion_token} {query}"

        enc = self.tokenizer(
            conditioned_q, response,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        ids  = enc["input_ids"].to(self.device)
        mask = enc["attention_mask"].to(self.device)

        with torch.no_grad():
            r_emp, r_rel = self.model(ids, mask)

        r_emp = r_emp.item()
        r_rel = r_rel.item()
        α, β  = EMOTION_WEIGHTS.get(emotion.lower(), (0.5, 0.5))
        r_tot = α * r_emp + β * r_rel

        return r_emp, r_rel, r_tot

    def select(self, query: str, candidates: list, emotion: str = "neutral") -> tuple:
        """
        Select the best candidate using Thompson Sampling over emotion-conditioned rewards.

        Returns:
            (best_response: str, metadata: dict)
        """
        if not candidates:
            return "", {}

        if not self.is_ready():
            print("[EARS] No model — returning first candidate.")
            return candidates[0], {"method": "fallback", "emotion": emotion}

        emotion = emotion.lower() if emotion else "neutral"
        if emotion not in EMOTION_WEIGHTS:
            emotion = "unknown"

        n = len(candidates)

        # Score all candidates with emotion conditioning
        emp_scores = []
        rel_scores = []
        tot_scores = []

        for c in candidates:
            r_emp, r_rel, r_tot = self._score_candidate(query, c, emotion)
            emp_scores.append(r_emp)
            rel_scores.append(r_rel)
            tot_scores.append(r_tot)

        # Thompson Sampling over total reward scores
        sampler = ThompsonSampler(n_candidates=n)
        sampler.update(tot_scores)
        selected_idx  = sampler.sample()
        ts_samples    = list(np.random.beta(sampler.alphas, sampler.betas))
        uncertainties = sampler.get_uncertainty()

        α, β = EMOTION_WEIGHTS.get(emotion, (0.5, 0.5))

        metadata = {
            "selected_idx":  selected_idx,
            "r_empathy":     [round(s, 4) for s in emp_scores],
            "r_relevance":   [round(s, 4) for s in rel_scores],
            "total_scores":  [round(s, 4) for s in tot_scores],
            "ts_samples":    [round(s, 4) for s in ts_samples],
            "uncertainties": [round(s, 6) for s in uncertainties],
            "alpha_weight":  α,
            "beta_weight":   β,
            "emotion":       emotion,
            "method":        "EARS-Thompson",
        }

        print(f"[EARS] Emotion: {emotion} | α={α} β={β}")
        print(f"[EARS] r_empathy:   {[f'{s:.3f}' for s in emp_scores]}")
        print(f"[EARS] r_relevance: {[f'{s:.3f}' for s in rel_scores]}")
        print(f"[EARS] total:       {[f'{s:.3f}' for s in tot_scores]}")
        print(f"[EARS] TS samples:  {[f'{s:.3f}' for s in ts_samples]}")
        print(f"[EARS] Selected candidate {selected_idx+1}/{n}")

        return candidates[selected_idx], metadata


# ══════════════════════════════════════════════════════════════════════════════
# Backward-compatible wrapper matching RLHFRanker interface
# ══════════════════════════════════════════════════════════════════════════════
class RLHFRanker(EARSRanker):
    """
    Drop-in replacement for the original RLHFRanker.
    Adds emotion parameter to best_of_n().
    """

    def best_of_n(self, query: str, candidates: list, emotion: str = "neutral") -> tuple:
        """
        Returns (best_response, total_reward_score) — same signature as original
        RLHFRanker.best_of_n() but now emotion-conditioned.
        """
        best, metadata = self.select(query, candidates, emotion)
        if not metadata:
            return best, 0.0
        idx   = metadata.get("selected_idx", 0)
        score = metadata.get("total_scores", [0.0])[idx] if metadata.get("total_scores") else 0.0
        return best, score