from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceGroup, Mentionee
)
import json, os, re
from datetime import datetime

app = Flask(__name__)

# --- LINE SECRETS (from you) ---
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

OWNER_ID = "U75fd18c523f2254bb7f1553ee39454fb"

# Files
ROLES_FILE = "roles.json"
BANNED_WORDS_FILE = "banned_words.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

roles = load_json(ROLES_FILE)
banned_words = load_json(BANNED_WORDS_FILE)

def mention_to_user_id(mention_text, mentionees):
    for m in mentionees:
        if m.type == "user":
            return m.user_id
    return None

def kick_user_from_group(group_id, user_id, event):
    try:
        line_bot_api.kickout_from_group(group_id, user_id)
    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ Unable to kick user. Bot might not have permission."))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    group_id = event.source.group_id if isinstance(event.source, SourceGroup) else None
    mentionees = event.message.mention.mentionees if hasattr(event.message, "mention") else []
    
    is_owner = user_id == OWNER_ID
    is_mod = roles.get("mods", {}).get(user_id, False)
    authorized = is_owner or is_mod

    # Block banned users
    if roles.get("banned", {}).get(user_id):
        return

    # Check for banned words
    if any(bad_word in text.lower() for bad_word in banned_words):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🚫 That word is banned here."))
        return

    # Public Commands
    if text == "/help":
        help_text = (
            "**Admin Commands:**\n"
            "/addban <word>\n/removeban <word>\n/mod @<user>\n/ban @<user>\n/unban @<user>\n"
            "/announce <message>\n/kick @<user>\n/botname <newname>\n/purge\n\n"
            "**Public Commands:**\n"
            "/time\n.lurkmsg"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))
        return

    if text == "/time":
        utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🕒 Current UTC time:\n{utc_time}"))
        return

    if text == ".lurkmsg":
        msg = f"👀 Tracking active vs inactive members... (simulated)"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text.startswith("/botname"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            name = parts[1]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🤖 My new name is now: {name} (simulated)"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /botname NewBotName"))
        return

    if text == "/purge":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧹 Purging recent messages... (simulated)"))
        return

    if not authorized:
        return

    # Admin Commands
    if text.startswith("/addban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].lower()
            if word not in banned_words:
                banned_words.append(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ Added banned word: {word}"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"⚠️ Word already banned: {word}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /addban <word>"))
        return

    if text.startswith("/removeban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].lower()
            if word in banned_words:
                banned_words.remove(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ Removed banned word: {word}"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"⚠️ Word not found: {word}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /removeban <word>"))
        return

    if text.startswith("/mod"):
        if mentionees:
            target_id = mention_to_user_id(text, mentionees)
            if target_id:
                roles.setdefault("mods", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🛡️ User promoted to mod."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /mod @user"))
        return

    if text.startswith("/ban"):
        if mentionees:
            target_id = mention_to_user_id(text, mentionees)
            if target_id:
                roles.setdefault("banned", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                if group_id:
                    kick_user_from_group(group_id, target_id, event)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /ban @user"))
        return

    if text.startswith("/unban"):
        if mentionees:
            target_id = mention_to_user_id(text, mentionees)
            if target_id in roles.get("banned", {}):
                del roles["banned"][target_id]
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ User unbanned."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /unban @user"))
        return

    if text.startswith("/kick"):
        if mentionees:
            target_id = mention_to_user_id(text, mentionees)
            if target_id and group_id:
                kick_user_from_group(group_id, target_id, event)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /kick @user"))
        return

    if text.startswith("/announce"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and group_id:
            msg = parts[1]
            line_bot_api.push_message(group_id, TextSendMessage(text=f"📢 Announcement:\n{msg}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /announce <message>"))
        return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
