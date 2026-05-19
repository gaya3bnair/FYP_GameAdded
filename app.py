import os
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from chromadb import PersistentClient
import redis
import bcrypt
import numpy as np
import soundfile as sf
import torch
import uuid
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from sarvam_utils import detect_language, ml_to_en, en_to_ml
from condition.condition_module import start_condition_test, process_answer, user_sessions
from agentic_kg.graph_agent import AgenticKnowledgeGraph
from prompts import QA_PROMPT, SUMMARY_PROMPT
from rlhf_inference_ears import RLHFRanker

load_dotenv()

# ─── Condition hint keywords ───────────────────────────────────────────────────
ANXIETY_HINTS = ["worried", "anxious", "panic", "stress", "overthinking", "fear"]
ADHD_HINTS    = ["can't focus", "distracted", "procrastinating", "forgetting", "not finishing"]
OCD_HINTS     = ["checking", "repeat", "obsession", "intrusive", "cleaning", "ritual"]

# ─── Model inits ───────────────────────────────────────────────────────────────
whisper_model = WhisperModel("small", device="cpu")

SER_MODEL_PATH           = "ser_model"
SER_CONFIDENCE_THRESHOLD = 0.70
SER_ID_TO_LABEL = {
    0: "neutral",
    1: "happy",
    2: "sad",
    3: "angry",
    4: "fearful",
}

def load_ser_model(model_path: str):
    if not os.path.exists(model_path):
        print(f"[SER] Model not found at {model_path}. Will use energy heuristic only.")
        return None, None
    feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_path)
    ser = Wav2Vec2ForSequenceClassification.from_pretrained(model_path)
    ser.eval()
    print(f"[SER] Loaded fine-tuned model from {model_path}")
    return feature_extractor, ser

ser_feature_extractor, ser_model = load_ser_model(SER_MODEL_PATH)

rlhf_ranker = RLHFRanker()

analyzer = SentimentIntensityAnalyzer()

kg_agent = AgenticKnowledgeGraph()

# ─── Config ────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER        = "uploads"
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
ALLOWED_EXTENSIONS   = {"txt", "pdf"}
CHUNK_SIZE           = 500
CHUNK_OVERLAP        = 50
MAX_HISTORY_MESSAGES = 10

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PERSIST_DIR,   exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SECRET_KEY"]    = os.getenv("SECRET_KEY", "your-secret-key-change-this")

# ─── Redis ─────────────────────────────────────────────────────────────────────
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
    db=0,
    decode_responses=True,
)

# ─── Embeddings + LLM ──────────────────────────────────────────────────────────
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
model           = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant")

# ─── Email validation ──────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))

# ─── Language helpers ──────────────────────────────────────────────────────────
def reply_language_from_text(text):
    return "malayalam" if detect_language(text) == "malayalam" else "english"

def reply_in_user_language(english_text, lang):
    return en_to_ml(english_text) if lang == "malayalam" else english_text

# ─── EARS emotion helper ───────────────────────────────────────────────────────
def score_to_emotion(score: float) -> str:
    """Map VADER compound score to an emotion label for EARS reward conditioning."""
    if score <= -0.5:  return "sad"
    if score <= -0.1:  return "fearful"
    if score >= 0.5:   return "happy"
    return "neutral"

# ─── Condition helpers ─────────────────────────────────────────────────────────
def detect_condition_hint(text):
    text = text.lower()
    if any(w in text for w in ANXIETY_HINTS): return "anxiety"
    if any(w in text for w in ADHD_HINTS):    return "adhd"
    if any(w in text for w in OCD_HINTS):     return "ocd"
    return None

def can_suggest_test(email):
    key       = f"last_suggestion:{email}"
    last_time = redis_client.get(key)
    if last_time:
        if datetime.now() - datetime.fromisoformat(last_time) < timedelta(minutes=10):
            return False
    redis_client.set(key, datetime.now().isoformat())
    return True

# ─── File helpers ──────────────────────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── ChromaDB helpers ──────────────────────────────────────────────────────────
def get_user_collection_name(email):
    return f"user_{hashlib.md5(email.encode()).hexdigest()[:16]}"

def get_user_chroma_client(email):
    chroma_client   = PersistentClient(path=PERSIST_DIR)
    collection_name = get_user_collection_name(email)
    try:
        collection = chroma_client.get_collection(collection_name)
    except:
        collection = chroma_client.create_collection(collection_name)
    return chroma_client, collection, collection_name

# ─── Redis chat helpers ────────────────────────────────────────────────────────
def store_chat_message(email, role, message):
    chat_key     = f"chat_history:{email}"
    message_data = {
        "role":      role,
        "message":   message,
        "timestamp": datetime.now().isoformat()
    }
    redis_client.rpush(chat_key, json.dumps(message_data))
    redis_client.ltrim(chat_key, -(MAX_HISTORY_MESSAGES * 2), -1)

def get_chat_history(email):
    chat_key = f"chat_history:{email}"
    return [json.loads(m) for m in redis_client.lrange(chat_key, 0, -1)]

def get_user_summary(email):
    return redis_client.get(f"user_summary:{email}") or ""

def update_user_summary(email, new_summary):
    redis_client.set(f"user_summary:{email}", new_summary)

def build_conversation_context(email):
    history = get_chat_history(email)
    if not history:
        return ""
    parts = []
    for msg in history[-MAX_HISTORY_MESSAGES:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        parts.append(f"{role}: {msg['message']}")
    return "\n".join(parts)

def get_message_count(email):
    return int(redis_client.get(f"msg_count:{email}") or 0)

def increment_message_count(email):
    redis_client.incr(f"msg_count:{email}")

# ─── Ingest ────────────────────────────────────────────────────────────────────
def ingest_file_to_chroma(path, filename, email):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'txt':
        docs = TextLoader(path, encoding='utf-8').load()
    elif ext == 'pdf':
        docs = PyPDFLoader(path).load()
    else:
        return 0
    split_docs = CharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).split_documents(docs)
    _, collection, _ = get_user_chroma_client(email)
    texts     = [d.page_content for d in split_docs]
    metadatas = [d.metadata     for d in split_docs]
    ids       = [f"{filename}-{i}" for i in range(len(split_docs))]
    collection.add(
        ids=ids, metadatas=metadatas, documents=texts,
        embeddings=embedding_model.embed_documents(texts)
    )
    return len(split_docs)

# ─── RLHF / EARS helpers ───────────────────────────────────────────────────────
def generate_n_responses(query: str, retriever, n: int = 3) -> list:
    candidates   = []
    temperatures = [0.3, 0.7, 1.0]
    for i in range(n):
        try:
            temp_model = ChatGroq(
                api_key=GROQ_API_KEY,
                model="llama-3.1-8b-instant",
                temperature=temperatures[i % len(temperatures)]
            )
            chain  = RetrievalQA.from_chain_type(
                llm=temp_model,
                retriever=retriever,
                return_source_documents=False,
                chain_type_kwargs={"prompt": QA_PROMPT}
            )
            result = chain({"query": query})
            candidates.append(result["result"])
        except Exception as e:
            print(f"[EARS] Candidate {i+1} generation failed: {e}")
    return candidates if candidates else ["I'm here to help. Could you tell me more?"]

def store_feedback(email: str, message_id: str, query: str, response: str,
                   rating: int, emotion: str = "neutral"):
    """Store user feedback including detected emotion for EARS training."""
    key  = f"feedback:{email}:{message_id}"
    data = {
        "query":     query,
        "response":  response,
        "rating":    rating,
        "emotion":   emotion,
        "email":     email,
        "timestamp": datetime.now().isoformat(),
    }
    redis_client.set(key, json.dumps(data))
    print(f"[EARS] Feedback stored — {'👍' if rating == 1 else '👎'} | emotion={emotion} | {message_id}")

# ─── Audio helpers ─────────────────────────────────────────────────────────────
def transcribe_audio(path):
    segments, _ = whisper_model.transcribe(path)
    return " ".join(s.text for s in segments).strip()

def energy_heuristic(audio: np.ndarray) -> tuple:
    energy = np.mean(audio ** 2)
    if energy < 0.001:   return "low_energy",   0.9
    elif energy < 0.005: return "mild_distress", 0.7
    else:                return "neutral",        0.8

def detect_audio_emotion(file_path: str) -> str:
    TARGET_SR   = 16000
    MAX_SAMPLES = TARGET_SR * 5
    wav_path    = "converted_audio.wav"

    subprocess.run(
        ["ffmpeg", "-i", file_path, "-ac", "1", "-ar", str(TARGET_SR), wav_path, "-y"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        audio, sr = sf.read(wav_path)
        if sr != TARGET_SR:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
        audio   = audio.astype(np.float32)
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
    except Exception as e:
        print(f"[SER] Audio load error: {e}. Defaulting to neutral.")
        return "neutral"

    energy_label, _ = energy_heuristic(audio)

    if ser_model is None or ser_feature_extractor is None:
        print("[SER] No model loaded — using energy heuristic.")
        return energy_label

    try:
        audio_input = (
            audio[:MAX_SAMPLES] if len(audio) > MAX_SAMPLES
            else np.pad(audio, (0, MAX_SAMPLES - len(audio)))
        )
        inputs = ser_feature_extractor(
            audio_input, sampling_rate=TARGET_SR,
            return_tensors="pt", padding=False
        )
        with torch.no_grad():
            outputs = ser_model(input_values=inputs["input_values"])

        probs                    = torch.softmax(outputs.logits[0], dim=-1)
        confidence, predicted_id = probs.max(dim=-1)
        confidence               = confidence.item()
        model_label              = SER_ID_TO_LABEL.get(predicted_id.item(), "neutral")

        print(f"[SER] Model → {model_label} (conf={confidence:.2f}) | Energy → {energy_label}")

        if confidence >= SER_CONFIDENCE_THRESHOLD:
            return model_label
        else:
            print(f"[SER] Low confidence ({confidence:.2f}) — falling back to energy heuristic.")
            return energy_label
    except Exception as e:
        print(f"[SER] Model inference error: {e}. Using energy heuristic.")
        return energy_label


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("chat.html")


# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/signup", methods=["POST"])
def signup():
    data     = request.get_json()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name     = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400

    user_key = f"user:{email}"
    if redis_client.exists(user_key):
        return jsonify({"error": "User already exists"}), 400

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    redis_client.hset(user_key, mapping={
        "email": email, "name": name,
        "password_hash": password_hash,
        "created_at": datetime.now().isoformat()
    })
    return jsonify({"message": "Signup successful", "email": email}), 201


@app.route("/signin", methods=["POST"])
def signin():
    data     = request.get_json()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user_data = redis_client.hgetall(f"user:{email}")
    if not user_data:
        return jsonify({"error": "Invalid credentials"}), 401
    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user_data.get("password_hash", "").encode("utf-8")
    ):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_email"] = email
    session["user_name"]  = user_data.get("name", "")
    session.permanent     = True
    app.permanent_session_lifetime = timedelta(days=7)
    return jsonify({
        "message": "Signin successful",
        "email":   email,
        "name":    user_data.get("name", "")
    }), 200


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return jsonify({"message": "Signout successful"}), 200


@app.route("/me", methods=["GET"])
def get_current_user():
    if "user_email" not in session:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "email": session["user_email"],
        "name":  session.get("user_name", "")
    }), 200


# ─── Upload ────────────────────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename  = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        chunks = ingest_file_to_chroma(file_path, filename, session["user_email"])
        return jsonify({
            "message": f"Uploaded and processed {chunks} chunks to your personal knowledge base."
        })
    return jsonify({"error": "Invalid file type"}), 400


# ─── EARS Feedback ─────────────────────────────────────────────────────────────
@app.route("/feedback", methods=["POST"])
def submit_feedback():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data       = request.get_json()
    message_id = data.get("message_id", "")
    query      = data.get("query",      "")
    response   = data.get("response",   "")
    rating     = data.get("rating")
    emotion    = data.get("emotion",    "neutral")

    if not message_id or not query or not response or rating not in (0, 1):
        return jsonify({"error": "Invalid feedback data"}), 400

    store_feedback(
        email=session["user_email"],
        message_id=message_id,
        query=query,
        response=response,
        rating=rating,
        emotion=emotion,
    )
    return jsonify({"message": "Feedback recorded. Thank you!"}), 200


# ─── Voice chat ────────────────────────────────────────────────────────────────
@app.route("/voice_chat", methods=["POST"])
def voice_chat():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    file     = request.files["audio"]
    filepath = "temp_audio.webm"
    file.save(filepath)
    email = session["user_email"]

    text          = transcribe_audio(filepath)
    audio_emotion = detect_audio_emotion(filepath)
    text_score    = analyzer.polarity_scores(text)["compound"]

    print(f"Transcribed: {text}")
    print(f"Audio emotion: {audio_emotion}")
    print(f"Text sentiment: {text_score}")

    store_chat_message(email, "user", text)
    print("VOICE ROUTE HIT")

    # Emotional routing
    if text_score <= -0.5 or (audio_emotion in ("sad", "fearful") and text_score < 0):
        comforting = (
            "I can sense that you might be going through something really difficult. "
            "You're not alone, and I'm here to listen. "
            "If these feelings persist, please consider speaking to a mental health professional — "
            "it's one of the strongest things you can do for yourself."
        )
        message_id = str(uuid.uuid4())
        store_chat_message(email, "bot", comforting)
        return jsonify({
            "transcribed_text": text,
            "audio_emotion":    audio_emotion,
            "response":         comforting,
            "message_id":       message_id,
            "emotion":          audio_emotion,
        })

    elif audio_emotion == "angry":
        comforting = (
            "I can hear some frustration in your voice. "
            "That's completely valid. Take a breath — I'm here to help."
        )
        message_id = str(uuid.uuid4())
        store_chat_message(email, "bot", comforting)
        return jsonify({
            "transcribed_text": text,
            "audio_emotion":    audio_emotion,
            "response":         comforting,
            "message_id":       message_id,
            "emotion":          audio_emotion,
        })

    # happy / neutral → RAG pipeline
    conversation_context = build_conversation_context(email)
    long_term_summary    = get_user_summary(email)

    chroma_client, _, collection_name = get_user_chroma_client(email)
    vectorstore = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embedding_model
    )
    retriever = vectorstore.as_retriever()

    enhanced_query = f"""
Long-term memory:
{long_term_summary}

Recent conversation:
{conversation_context}

Current question:
{text}
""" if conversation_context else text

    # KG check first
    kg_result = kg_agent.run(text)
    print(f"\n=== KG RESULT (voice) ===\n{kg_result}\n=========================\n")

    if kg_result["detected"]:
        print("Voice: Using KNOWLEDGE GRAPH pipeline")
        bot_response = kg_result["response"]

    elif rlhf_ranker.is_ready():
        candidates   = generate_n_responses(enhanced_query, retriever, n=3)
        bot_response, reward_score = rlhf_ranker.best_of_n(
            text, candidates, emotion=audio_emotion
        )
        print(f"[EARS] Voice Best-of-3 selected (reward={reward_score:.3f}, emotion={audio_emotion})")

    else:
        qa_chain     = RetrievalQA.from_chain_type(
            llm=model, retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": QA_PROMPT}
        )
        bot_response = qa_chain({"query": enhanced_query})["result"]
        print("[EARS] No reward model yet — using single response.")

    message_id = str(uuid.uuid4())
    store_chat_message(email, "bot", bot_response)
    return jsonify({
        "transcribed_text": text,
        "audio_emotion":    audio_emotion,
        "response":         bot_response,
        "message_id":       message_id,
        "emotion":          audio_emotion,
    })


# ─── Text chat ─────────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    email        = session["user_email"]
    data         = request.get_json()
    raw_query    = (data.get("query") or "").strip()
    voice_locale = (data.get("voice_locale") or "").strip() or None

    if not raw_query:
        return jsonify({"error": "Empty query"}), 400

    # Language detection
    lang     = reply_language_from_text(raw_query)
    query_en = ml_to_en(raw_query) if lang == "malayalam" else raw_query

    if not query_en or not str(query_en).strip():
        return jsonify({"error": "Empty query"}), 400

    # ── Condition test module ──────────────────────────────────────────────────
    if email in user_sessions:
        response = process_answer(email, raw_query)
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", response)
        return jsonify({"response": response})

    query_lower = raw_query.lower()
    if "check adhd" in query_lower:
        q = start_condition_test(email, "adhd")
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", q)
        return jsonify({"response": f"🧠 ADHD Screening Started\n\n{q}\n\n(Answer 0–4)"})
    elif "check anxiety" in query_lower:
        q = start_condition_test(email, "anxiety")
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", q)
        return jsonify({"response": f"😰 Anxiety Screening Started\n\n{q}\n\n(Answer 0–4)"})
    elif "check ocd" in query_lower:
        q = start_condition_test(email, "ocd")
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", q)
        return jsonify({"response": f"🔁 OCD Screening Started\n\n{q}\n\n(Answer 0–4)"})

    # ── Sentiment + EARS emotion ───────────────────────────────────────────────
    score        = analyzer.polarity_scores(query_en)["compound"]
    text_emotion = score_to_emotion(score)

    # ── Condition suggestion ───────────────────────────────────────────────────
    condition_hint  = detect_condition_hint(query_en)
    suggestion_text = ""
    if condition_hint and can_suggest_test(email):
        if condition_hint == "anxiety":
            suggestion_text = "\n\n💡 You seem a bit stressed. Would you like to try a quick anxiety check? (type: check anxiety)"
        elif condition_hint == "adhd":
            suggestion_text = "\n\n💡 Having focus issues? You can try an ADHD self-check (type: check adhd)"
        elif condition_hint == "ocd":
            suggestion_text = "\n\n💡 If repetitive thoughts are bothering you, you can try an OCD check (type: check ocd)"

    print(f"\n=== Sentiment: {score} | Emotion: {text_emotion} | Lang: {lang} | Voice locale: {voice_locale} ===\n")

    # ── Emotional routing ──────────────────────────────────────────────────────
    if score <= -0.5:
        comforting_en = (
            "I'm really sorry you're feeling this way. "
            "You're not alone, and I'm right here with you. "
            "Would you like to talk about what's troubling you? "
            "If you're feeling really bad, please seek professional help."
        )
        comforting = reply_in_user_language(comforting_en, lang)
        message_id = str(uuid.uuid4())
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", comforting)
        return jsonify({
            "response":   comforting,
            "message_id": message_id,
            "emotion":    text_emotion,
        })

    elif -0.5 < score < -0.1:
        gentle_en = (
            "I can hear that you're going through something difficult. "
            "I'm here for you. How can I support you right now?"
        )
        gentle     = reply_in_user_language(gentle_en, lang)
        message_id = str(uuid.uuid4())
        store_chat_message(email, "user", raw_query)
        store_chat_message(email, "bot", gentle)
        return jsonify({
            "response":   gentle,
            "message_id": message_id,
            "emotion":    text_emotion,
        })

    store_chat_message(email, "user", raw_query)

    # ── Context ────────────────────────────────────────────────────────────────
    conversation_context = build_conversation_context(email)
    long_term_summary    = get_user_summary(email)

    condition_data = redis_client.get(f"user_condition:{email}")
    if condition_data:
        cond, severity       = condition_data.split(":")
        conversation_context = (
            f"\nUser recently completed a {cond.upper()} assessment with result: {severity}.\n"
            + conversation_context
        )

    chroma_client, _, collection_name = get_user_chroma_client(email)
    vectorstore = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embedding_model
    )
    retriever = vectorstore.as_retriever()

    if conversation_context:
        enhanced_query = f"""
Long-term memory about the user:
{long_term_summary}

Previous conversation:
{conversation_context}

Current question: {query_en}
"""
    else:
        enhanced_query = query_en

    if lang == "english":
        enhanced_query += "\n\n(Important: The user is using English. Answer in English only.)"
    else:
        enhanced_query += (
            "\n\n(Important: The user wrote in Malayalam. "
            "Answer in English only; the server will translate to Malayalam.)"
        )

    # ── KG check ──────────────────────────────────────────────────────────────
    kg_result = kg_agent.run(query_en)
    print(f"\n=== KG RESULT ===\n{kg_result}\n=================\n")

    if kg_result["detected"]:
        print("Using KNOWLEDGE GRAPH pipeline")
        bot_response = kg_result["response"]

    elif rlhf_ranker.is_ready():
        print("Using VECTOR RAG + EARS Best-of-3 pipeline")
        candidates   = generate_n_responses(enhanced_query, retriever, n=3)
        bot_response, reward_score = rlhf_ranker.best_of_n(
            query_en, candidates, emotion=text_emotion
        )
        print(f"[EARS] Best-of-3 selected (reward={reward_score:.3f}, emotion={text_emotion})")

    else:
        print("Using VECTOR RAG pipeline (no reward model yet)")
        qa_chain     = RetrievalQA.from_chain_type(
            llm=model, retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": QA_PROMPT}
        )
        bot_response = qa_chain.invoke({"query": enhanced_query})["result"]

    bot_response += suggestion_text

    if lang == "malayalam":
        bot_response = en_to_ml(bot_response)

    message_id = str(uuid.uuid4())
    store_chat_message(email, "bot", bot_response)

    # Long-term summary update every 5 messages
    increment_message_count(email)
    if get_message_count(email) % 5 == 0:
        summary_chain   = SUMMARY_PROMPT | model
        updated_summary = summary_chain.invoke({
            "old_summary":  long_term_summary,
            "conversation": build_conversation_context(email),
        }).content
        update_user_summary(email, updated_summary)

    return jsonify({
        "response":   bot_response,
        "message_id": message_id,
        "emotion":    text_emotion,
    })


# ─── History ───────────────────────────────────────────────────────────────────
@app.route("/history", methods=["GET"])
def get_history():
    if "user_email" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"history": get_chat_history(session["user_email"])}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False, ssl_context='adhoc')