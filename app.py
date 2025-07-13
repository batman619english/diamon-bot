import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime

app = Flask(__name__)

# LINE credentials
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Owner ID
owner_id = "U4dbc4dee4747e4f8ce6fe6a03d481667"

# JSON file for memory
DATA_FILE = "user_roles.json"

def load_roles():
    if not os.path.exists(DATA_FILE):
        return {"mods": [], "banned": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_roles(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    print("Request body:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature.")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    print(f"👤 Message from user ID: {user_id} — Text: {text}")

    roles = load_roles()

    if user_id != owner_id:
        # Silent ignore if not owner
        return

    if text == "/time":
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Current time: {current_time}")
        )

    elif text == ".help owners":
        owner_commands = """👑 Owner Commands:
• /mod @user - Promote someone to mod
• /ban @user - Ban a user
• /unban @user - Unban a user
• /announce [text] - Send a global message
• /purge - Clean recent messages
• /botname [newname] - Change bot name"""
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=owner_commands)
        )

    elif text.startswith("/mod @"):
        target = text.replace("/mod ", "").strip()
        if target not in roles["mods"]:
            roles["mods"].append(target)
            save_roles(roles)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ {target} is now a mod.")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ℹ️ {target} is already a mod.")
            )

    elif text.startswith("/ban @"):
        target = text.replace("/ban ", "").strip()
        if target not in roles["banned"]:
            roles["banned"].append(target)
            save_roles(roles)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"🚫 {target} has been banned.")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ℹ️ {target} is already banned.")
            )

    elif text.startswith("/unban @"):
        target = text.replace("/unban ", "").strip()
        if target in roles["banned"]:
            roles["banned"].remove(target)
            save_roles(roles)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"♻️ {target} has been unbanned.")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ℹ️ {target} is not in the banned list.")
            )

    elif text.startswith("/announce "):
        message = text.replace("/announce ", "")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"📢 Announcement: {message}")
        )

    elif text.startswith("/purge"):
        # Purge simulation
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🧹 Purge complete (simulated).")
        )

    elif text.startswith("/botname "):
        new_name = text.replace("/botname ", "").strip()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"🤖 Bot name changed to: {new_name} (simulated)")
        )

    else:
        pass  # No reply to unknown commands

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
