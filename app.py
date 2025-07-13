import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# Put your channel access token and secret here
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_CHANNEL_ACCESS_TOKEN'
LINE_CHANNEL_SECRET = 'YOUR_CHANNEL_SECRET'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

owner_id = "WITsayiangod"  # Replace with your LINE user ID

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id

    if text.startswith('/time'):
        from datetime import datetime
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Current time: {current_time}")
        )

    elif text == '.help owners':
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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
