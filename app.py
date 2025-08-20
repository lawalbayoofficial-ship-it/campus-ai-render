import os
import requests
from flask import Flask, request, jsonify

# === ENV ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_API_KEY")  # optional, only needed for AI replies

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN env var")

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Hugging Face endpoints (free, change later if you want)
HF_CONVO_MODEL = "facebook/blenderbot-400M-distill"     # conversational
HF_SUMMARY_MODEL = "facebook/bart-large-cnn"            # summarization

def hf_generate(model: str, text: str) -> str:
    """Call Hugging Face Inference API. Returns a string or fallback."""
    if not HF_TOKEN:
        # If no HF token, do a simple fallback (echo/placeholder)
        return "AI mode is off right now. Add HF_API_KEY to enable smart replies."
    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=25,
        )
        if r.status_code != 200:
            return "AI is a bit busy. Try again in a moment."
        data = r.json()
        # Handle both array/object shapes
        if isinstance(data, list) and data:
            return data[0].get("generated_text") or data[0].get("summary_text") or "…"
        if isinstance(data, dict):
            return data.get("generated_text") or data.get("summary_text") or "…"
        return "…"
    except Exception:
        return "Network hiccup reaching the AI. Please try again."

def send_text(chat_id: int, text: str):
    try:
        requests.post(TELEGRAM_SEND_URL, json={"chat_id": chat_id, "text": text}, timeout=15)
    except Exception:
        pass

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "Campus AI is live.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = (update.get("message") or update.get("edited_message")) or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = msg.get("text", "")

    if not chat_id:
        return jsonify(ok=True)

    # Basic routing
    low = (text or "").lower()
    if low.startswith("/start"):
        send_text(chat_id,
                  "👋 Welcome to Campus AI!\n"
                  "I can chat, summarize notes, and share campus news.\n\n"
                  "Try:\n"
                  "• /note Photosynthesis is the process...\n"
                  "• /news\n"
                  "• Or just say hi.")
        return jsonify(ok=True)

    if low.startswith("/news") or "campus news" in low or "what's happening" in low:
        news_items = [
            "🎤 SU Press Night – Tue 5PM, Auditorium",
            "📚 Faculty of Science Seminar – Thu 12PM, LT1",
            "⚽ Inter-Faculty Final – Fri 4PM, Stadium"
        ]
        send_text(chat_id, "📰 Campus News:\n" + "\n".join(f"• {n}" for n in news_items))
        return jsonify(ok=True)

    if low.startswith("/note ") or "summarize" in low or "tl;dr" in low:
        # Summarize the rest of the text
        raw = text[6:].strip() if low.startswith("/note ") else text
        if not raw:
            send_text(chat_id, "Send like: /note <your notes here>")
            return jsonify(ok=True)
        summary = hf_generate(HF_SUMMARY_MODEL, raw)
        send_text(chat_id, f"📚 Summary:\n{summary}")
        return jsonify(ok=True)

    # Default: conversational AI (or fallback)
    reply = hf_generate(HF_CONVO_MODEL, text or "Hello")
    send_text(chat_id, reply)
    return jsonify(ok=True)
