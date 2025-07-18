from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, SourceGroup, SourceRoom
import firebase_admin
from firebase_admin import credentials, firestore
import json, os

app = Flask(__name__)

# Insert your LINE credentials here:
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

OWNER_ID = "U4dbc4dee4747e4f8ce6fe6a03d481667"

# Firebase init
db = None
try:
    firebase_config = json.loads(os.environ.get('__firebase_config', '{}'))
    if firebase_config.get("projectId"):
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        app.logger.info("✅ Firebase initialized")
    else:
        app.logger.info("🔹 Firebase config not set or dummy")
except Exception as e:
    app.logger.error("❌ Firebase init failed: %s", e)

COLL = f"artifacts/{os.environ.get('__app_id','default')}/public/data/line_bot_admins"

def is_admin(uid):
    if uid == OWNER_ID: 
        return True
    if db:
        try: 
            return db.collection(COLL).document(uid).get().exists
        except: 
            return False
    return False

def add_admin(uid):
    if not db: 
        return False
    try:
        db.collection(COLL).document(uid).set({'is_admin': True})
        return True
    except:
        return False

def remove_admin(uid):
    if not db: 
        return False
    try:
        db.collection(COLL).document(uid).delete()
        return True
    except:
        return False

def list_admins():
    if not db: 
        return []
    return [doc.id for doc in db.collection(COLL).stream()]

@app.route("/")
def home():
    return "Bot is live."

@app.route("/callback", methods=["POST"])
def callback():
    sig = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("ℹ️ Webhook received: %s", body)
    try:
        handler.handle(body, sig)
    except InvalidSignatureError:
        app.logger.error("❗Invalid signature")
        abort(400)
    except Exception as e:
        app.logger.error("❗Handler error: %s", e)
        abort(500)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    text = event.message.text.strip()
    uid = event.source.user_id
    reply = event.reply_token

    app.logger.info("Message from %s: %s", uid, text)

    # Only commands starting with '/'
    if not text.startswith("/"):
        return

    # Help or whoami
    if text == "/whoami":
        return line_bot_api.reply_message(reply, TextSendMessage(text=f"✅ Your user ID: {uid}"))

    # Admin commands (owner only)
    if uid == OWNER_ID:
        if text.startswith("/add_admin "):
            new_uid = text.split(" ", 1)[1].strip()
            ok = add_admin(new_uid)
            return line_bot_api.reply_message(reply, TextSendMessage(
                text="✅ Admin added." if ok else "❌ Failed to add admin"
            ))
        if text.startswith("/remove_admin "):
            target = text.split(" ",1)[1].strip()
            if target == OWNER_ID:
                return line_bot_api.reply_message(reply, TextSendMessage(text="🚫 Can't remove owner"))
            ok = remove_admin(target)
            return line_bot_api.reply_message(reply, TextSendMessage(
                text="✅ Admin removed." if ok else "❌ Failed to remove admin"
            ))

    # Admin or owner commands
    if not is_admin(uid):
        return line_bot_api.reply_message(reply, TextSendMessage(text="🚫 Not authorized"))

    if text == "/ping":
        return line_bot_api.reply_message(reply, TextSendMessage(text="✅ Pong — bot’s alive!"))

    if text == "/list_admins":
        admins = list_admins()
        admins_str = "\n".join(admins) if admins else "None"
        return line_bot_api.reply_message(reply, TextSendMessage(text=f"🏷️ Admin IDs:\n{admins_str}"))

    if text == "/leave_group":
        src = event.source
        if isinstance(src, SourceGroup):
            line_bot_api.reply_message(reply, TextSendMessage(text="👋 Leaving group"))
            return line_bot_api.leave_group(src.group_id)
        if isinstance(src, SourceRoom):
            line_bot_api.reply_message(reply, TextSendMessage(text="👋 Leaving room"))
            return line_bot_api.leave_room(src.room_id)
        return line_bot_api.reply_message(reply, TextSendMessage(text="⛔ Only in group/room"))

    # Unrecognized command
    return line_bot_api.reply_message(reply, TextSendMessage(text="❓ Unknown command"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
