import os
import json
from flask import Flask, request, abort
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceGroup, Mentionee
)

# === Replace these with your real token/secret ===
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='

# === Bot identity ===
OWNER_ID = 'U75fd18c523f2254bb7f1553ee39454fb'

# === File storage ===
ROLES_FILE = 'roles.json'
NAMES_FILE = 'names.json'
BANNED_WORDS_FILE = 'banned_words.json'
ACTIVITY_FILE = 'activity.json'

# === Bot setup ===
app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# === Load/save functions ===
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def mention_to_user_id(mention_text, names, event):
    if not isinstance(event.source, SourceGroup):
        return None
    mentionees = event.message.mention.mentionees if hasattr(event.message, 'mention') else []
    for m in mentionees:
        if isinstance(m, Mentionee):
            return m.user_id
    for uid, name in names.items():
        if mention_text.replace("@", "").lower() in name.lower():
            return uid
    return None

def kick_user_from_group(group_id, user_id, event):
    try:
        line_bot_api.kickout(group_id, user_id)
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Failed to kick user: {e}"))

# === Webhook endpoint ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# === Message handler ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    group_id = event.source.group_id if isinstance(event.source, SourceGroup) else None

    roles = load_json(ROLES_FILE)
    names = load_json(NAMES_FILE)
    banned_words = load_json(BANNED_WORDS_FILE)
    activity = load_json(ACTIVITY_FILE)

    # Record user name
    profile = line_bot_api.get_profile(user_id)
    names[user_id] = profile.display_name
    save_json(NAMES_FILE, names)

    # Check permissions
    is_owner = user_id == OWNER_ID
    is_mod = roles.get("mods", {}).get(user_id, False)
    authorized = is_owner or is_mod

    # ---------------- Admin + Public Commands ---------------- #
    if text == "/help":
        help_text = (
            "**Admin Commands:**\n"
            "/addban <word>\n"
            "/removeban <word>\n"
            "/mod @<user>\n"
            "/ban @<user>\n"
            "/unban @<user>\n"
            "/announce <message>\n"
            "/kick @<user>\n"
            "/botname <newname>\n"
            "/purge\n\n"
            "**Public Commands:**\n"
            "/time\n"
            ".lurkmsg"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))
        return

    if text == "/time":
        utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🕒 Current UTC time:\n{utc_time}"))
        return

    if text.startswith("/botname"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            bot_name = parts[1]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🤖 My new name is now: {bot_name} (simulated)"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /botname NewBotName"))
        return

    if text == "/purge":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧹 Purging recent messages... (simulated)"))
        return

    if not authorized:
        return

    if text.startswith("/addban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].strip().lower()
            if word not in banned_words:
                banned_words.append(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                msg = f"✅ Added banned word: {word}"
            else:
                msg = f"⚠️ Word already in ban list: {word}"
        else:
            msg = "Usage: /addban <word>"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text.startswith("/removeban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].strip().lower()
            if word in banned_words:
                banned_words.remove(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                msg = f"✅ Removed banned word: {word}"
            else:
                msg = f"⚠️ Word not found: {word}"
        else:
            msg = "Usage: /removeban <word>"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text.startswith("/mod"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id:
                roles.setdefault("mods", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🛡️ User promoted to moderator."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /mod @username"))
        return

    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id:
                roles.setdefault("banned", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                if group_id:
                    kick_user_from_group(group_id, target_id, event)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /ban @username"))
        return

    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id and target_id in roles.get("banned", {}):
                del roles["banned"][target_id]
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ User has been unbanned."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /unban @username"))
        return

    if text.startswith("/announce"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            msg = parts[1]
            if group_id:
                line_bot_api.push_message(group_id, TextSendMessage(text=f"📢 Announcement:\n{msg}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /announce <message>"))
        return

# === Run app ===
if __name__ == "__main__":
    app.run(debug=True)
