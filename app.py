from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os

app = Flask(__name__)

# Set your credentials here directly (as requested)
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

OWNER_ID = "U75fd18c523f2254bb7f1553ee39454fb"
mods = set()
banned_users = set()

@app.route("/")
def home():
    return "LINE Bot is running."

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
    user_id = event.source.user_id
    text = event.message.text

    # Basic ban check
    if user_id in banned_users:
        return

    is_owner = user_id == OWNER_ID
    is_mod = user_id in mods

    # Helper: extract mentioned user_ids
    mentionees = []
    if hasattr(event.message, "mention") and event.message.mention:
        mentionees = [m.user_id for m in event.message.mention.mentionees if m.user_id]

    # Secure command parser
    if text.startswith("/addban") and is_owner:
        banned_users.update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) banned."))

    elif text.startswith("/removeban") and is_owner:
        banned_users.difference_update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) unbanned."))

    elif text.startswith("/mod") and is_owner:
        mods.update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) promoted to mod."))

    elif text.startswith("/ban") and (is_owner or is_mod):
        banned_users.update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) banned."))

    elif text.startswith("/unban") and (is_owner or is_mod):
        banned_users.difference_update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) unbanned."))

    elif text.startswith("/announce") and (is_owner or is_mod):
        announcement = text.replace("/announce", "").strip()
        if announcement:
            line_bot_api.push_message(user_id, TextSendMessage(text=f"Announcement sent: {announcement}"))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Announcement done."))

    elif text.startswith("/botname"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="I'm Diamon Bot."))

    elif text.startswith("/purge") and (is_owner or is_mod):
        banned_users.clear()
        mods.clear()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="All bans and mods have been cleared."))

    elif text.startswith("/time"):
        from datetime import datetime
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))

    elif text.startswith(".lurkmsg"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="I'm watching silently 👀"))

    elif text.startswith("/admin") and is_owner:
        mods.update(mentionees)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User(s) promoted to admin."))

if __name__ == "__main__":
    app.run(debug=True)
