import os
import sys
import requests
from flask import Flask, request, jsonify
from gradio_client import Client

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SPACE_URL = os.environ.get("SPACE_URL")  # e.g., https://your-username-campus-ai-space.hf.space

if not TELEGRAM_BOT_TOKEN:
    print("❌ Missing TELEGRAM_BOT_TOKEN", flush=True)
    sys.exit(1)
if not SPACE_URL:
    print("❌ Missing SPACE_URL", flush=True)
    sys.exit(1)

TG_SEND = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
client = Client(SPACE_URL)  # Public Space so no token needed

app = Flask(__name__)

def send(chat_id, text):
    try:
        r = requests.post(TG_SEND, json={"chat_id": chat_id, "text": text}, timeout=20)
        print("sendMessage:", r.status_code, r.text[:200], flush=True)
    except Exception as e:
        print("send error:", e, flush=True)

@app.route("/", methods=["GET"])
def health():
    return "Campus AI (Render) alive", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    print("INCOMING:", update, flush=True)

    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = msg.get("text", "")

    if not chat_id:
        return jsonify(ok=True)

    # /start handler
    if str(text).strip().lower().startswith("/start"):
        send(chat_id, "👋 Hi! I’m Campus AI. Send me a message to chat.")
        return jsonify(ok=True)

    # Call your Space (fast, dedicated)
    try:
        # ChatInterface takes (message, history); we pass empty history for now
        reply = client.predict(text, [], api_name="/chat")
        if not isinstance(reply, str):
            reply = str(reply)
    except Exception as e:
        print("Space call error:", e, flush=True)
        reply = "AI Space is waking up. Please try again in a few seconds."

    send(chat_id, reply)
    return jsonify(ok=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
