"""
Malayalam ↔ English helpers for the chatbot (Helsinki-NLP OPUS-MT models).

- detect_language / user_language: Malayalam Unicode (U+0D00–U+0D7F) → "malayalam", else "english"
- ml_to_en: translate user input to English for sentiment + RAG + LLM
- en_to_ml: translate model output to Malayalam when the user used Malayalam
"""

import logging

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

# Load models once (lazy-friendly for import time)
ml_en_tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ml-en")
ml_en_model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-ml-en")
ml_en_model.eval()

en_ml_tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ml")
en_ml_model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-en-ml")
en_ml_model.eval()


def detect_language(text):
    """Return 'malayalam' if Malayalam script is present, else 'english'."""
    if not text or not str(text).strip():
        return "english"
    for ch in text:
        if "\u0D00" <= ch <= "\u0D7F":
            return "malayalam"
    return "english"


def user_language(text):
    """Alias: language of the user message for reply routing ('malayalam' | 'english')."""
    return detect_language(text)


def ml_to_en(text):
    """Translate Malayalam text to English for downstream NLP."""
    if not text or not str(text).strip():
        return text
    try:
        with torch.no_grad():
            inputs = ml_en_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            )
            outputs = ml_en_model.generate(**inputs, max_length=512)
        return ml_en_tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.warning("ml_to_en failed: %s", e)
        return text


def en_to_ml(text):
    """Translate English assistant reply to Malayalam."""
    if not text or not str(text).strip():
        return text
    try:
        with torch.no_grad():
            inputs = en_ml_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            )
            outputs = en_ml_model.generate(**inputs, max_length=512)
        return en_ml_tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.warning("en_to_ml failed: %s", e)
        return text
