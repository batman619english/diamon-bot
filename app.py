from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# Your LINE credentials
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRdMlxtae+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Your personal LINE ID (owner)
OWNER_ID = "U4dbc4dee4747e4f8ce6fe6a03d481667"

@app.route("/")
def home():
    return "Bot is live."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token

    # Only respond to commands that start with "/"
    if not text.startswith("/"):
        return

    # Only allow the OWNER to use commands
    if user_id != OWNER_ID:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ You are not authorized to use commands."))
        return

    # Handle commands
    if text.startswith("/ping"):
        line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ Pong! Bot is alive."))

    elif text.startswith("/kick"):
        line_bot_api.reply_message(reply_token, TextSendMessage(text="👢 Kick feature coming soon!"))

    elif text.startswith("/mod"):
        line_bot_api.reply_message(reply_token, TextSendMessage(text="🛡️ Mod feature coming soon!"))

    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="🤖 Unknown command. Try /ping or /mod"))

