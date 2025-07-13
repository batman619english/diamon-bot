import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Initialize Line API with credentials
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Process messages from users"""
    text = event.message.text.lower()
    
    # Simple command handling
    if text.startswith('/help'):
        help_message = "Diamon Bot Commands:\n"\
                      "/dice - Roll a 6-sided die\n"\
                      "/dice [number] - Roll custom die (e.g., /dice 20)\n"\
                      "/flip - Flip a coin\n"\
                      "/pick [options] - Pick random option\n"\
                      "/time - Show current time\n"\
                      "/help - Show this help"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_message)
        )
        
    elif text.startswith('/dice'):
        # Check if custom sides provided
        parts = text.split()
        sides = 6  # Default
        if len(parts) > 1 and parts[1].isdigit():
            sides = int(parts[1])
            
        result = random.randint(1, sides)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"🎲 You rolled: {result}")
        )
        
    elif text.startswith('/flip'):
        result = "Heads" if random.random() > 0.5 else "Tails"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"🪙 Coin flip: {result}!")
        )
        
    elif text.startswith('/pick'):
        parts = text.split(' ', 1)
        if len(parts) < 2:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Please provide options to pick from (separated by spaces)")
            )
        else:
            options = parts[1].split()
            if options:
                chosen = random.choice(options)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"I pick: {chosen}")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="Please provide options to pick from")
                )
                
    elif text.startswith('/time'):
        from datetime import datetime
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Current time: {current_time}")
        )

if __name__ == "__main__"
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)