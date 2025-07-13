import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime

app = Flask(__name__)

# === Your LINE credentials ===
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# === Replace this with your actual user ID (print it from the bot!) ===
owner_id = "U4dbc4dee4747e4f8ce6fe6a03d481667"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    # Log body for debugging
    print("Request body:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature. Check channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id

    print(f"👤 Message from user ID: {user_id} — Text: {text}")

    if text == "/time":
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Current time: {current_time}")
        )

    elif text == ".help owners":
        if user_id == owner_id:
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
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚫 You don't have permission to view owner commands.")
            )
    else:
        # Default echo
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"You said: {text}")
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
