from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, SourceGroup, SourceRoom

# Import Firebase modules
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

app = Flask(__name__)

# Your LINE credentials
LINE_CHANNEL_ACCESS_TOKEN = '64NaOsjydBzlZKcHsshIqwmZ7eoYc/kPZh85Ywd1cpi1D2KPbNKH+3s4RWafJW+edxzQyN09G/vaSRMlxte+d3ENEp2eqOsq9OxlWwgMVIOjSQQcKBo3coPVg3RPSZ8Ji3rBxh3hkkmf3nj+GXlQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '438c111da8cc1695732dd670a2003471'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Your personal LINE ID (owner) - This user has ultimate control
OWNER_ID = "U4dbc4dee4747e4f8ce6fe6a03d481667"

# --- Firebase Initialization ---
# Get Firebase config and app ID from environment variables provided by Canvas
try:
    firebase_config = json.loads(os.environ.get('__firebase_config'))
    app_id = os.environ.get('__app_id', 'default-app-id') # Default for local testing
except (json.JSONDecodeError, TypeError):
    print("Firebase config or app ID not found in environment variables. Using dummy config.")
    firebase_config = {
        "apiKey": "dummy", "authDomain": "dummy", "projectId": "dummy",
        "storageBucket": "dummy", "messagingSenderId": "dummy", "appId": "dummy"
    }
    app_id = 'default-app-id'

# Initialize Firebase Admin SDK (for server-side operations)
# This uses a dummy credential if __firebase_config is not available,
# which means Firestore operations won't work outside the Canvas environment
# without proper service account setup.
if firebase_config.get("projectId") != "dummy":
    try:
        # Firebase Admin SDK needs a service account credential for server-side access.
        # In a real deployment, you'd load this securely. For Canvas, the environment
        # provides the necessary config for client-side JS, but for Python backend,
        # you'd typically use a service account JSON file or environment variables.
        # For this example, we'll just initialize it to avoid errors if config is present,
        # but actual Firestore writes would fail without proper auth.
        # A more robust solution for Python backend would involve a service account key.
        # For now, we'll assume a basic initialization for demonstration within Canvas.
        if not firebase_admin._apps: # Initialize only if not already initialized
            firebase_admin.initialize_app(credentials.Certificate(firebase_config))
        db = firestore.client()
        print("Firebase initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}. Firestore operations will not work.")
        db = None # Set db to None if initialization fails
else:
    print("Firebase config is dummy. Firestore will not be used.")
    db = None

# Firestore collection path for storing admin IDs
# Using 'public/data' for shared access among bot users
ADMINS_COLLECTION_PATH = f"artifacts/{app_id}/public/data/line_bot_admins"

def is_admin(user_id):
    """Checks if a user is an admin or the owner."""
    if user_id == OWNER_ID:
        return True
    if db:
        try:
            doc_ref = db.collection(ADMINS_COLLECTION_PATH).document(user_id)
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            print(f"Error checking admin status for {user_id}: {e}")
            return False
    return False # If db is not initialized, no other admins can be checked

def add_admin_to_db(user_id):
    """Adds a user ID to the Firestore admins collection."""
    if db:
        try:
            doc_ref = db.collection(ADMINS_COLLECTION_PATH).document(user_id)
            doc_ref.set({'is_admin': True})
            return True
        except Exception as e:
            print(f"Error adding admin {user_id}: {e}")
            return False
    return False

def remove_admin_from_db(user_id):
    """Removes a user ID from the Firestore admins collection."""
    if db:
        try:
            doc_ref = db.collection(ADMINS_COLLECTION_PATH).document(user_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Error removing admin {user_id}: {e}")
            return False
    return False

def get_all_admins_from_db():
    """Retrieves all admin user IDs from Firestore."""
    admins = []
    if db:
        try:
            docs = db.collection(ADMINS_COLLECTION_PATH).stream()
            for doc in docs:
                admins.append(doc.id)
        except Exception as e:
            print(f"Error getting all admins: {e}")
    return admins

@app.route("/")
def home():
    return "Bot is live."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel secret.")
        abort(400)
    except Exception as e:
        app.logger.error(f"Error handling webhook: {e}")
        abort(500)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token

    # Log incoming message for debugging
    app.logger.info(f"Received message from {user_id}: {text}")

    # Only respond to commands that start with "/"
    if not text.startswith("/"):
        return

    # Check if the user is an admin or the owner
    is_current_user_admin = is_admin(user_id)

    # --- Commands accessible by OWNER_ID only ---
    if user_id == OWNER_ID:
        if text.startswith("/add_admin "):
            parts = text.split(" ")
            if len(parts) == 2:
                new_admin_id = parts[1].strip()
                if add_admin_to_db(new_admin_id):
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=f"✅ User {new_admin_id} added as admin."))
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ Failed to add admin. Check logs for details."))
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text="Usage: /add_admin <user_id>"))
            return # Command handled

        elif text.startswith("/remove_admin "):
            parts = text.split(" ")
            if len(parts) == 2:
                target_admin_id = parts[1].strip()
                if target_admin_id == OWNER_ID:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ Cannot remove the owner from admin list."))
                elif remove_admin_from_db(target_admin_id):
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=f"✅ User {target_admin_id} removed from admins."))
                else:
                    line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ Failed to remove admin. Check logs for details."))
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text="Usage: /remove_admin <user_id>"))
            return # Command handled

    # --- Commands accessible by OWNER_ID and registered Admins ---
    if not is_current_user_admin:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ You are not authorized to use this command."))
        return

    if text.startswith("/ping"):
        line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ Pong! Bot is alive."))

    elif text.startswith("/leave_group"):
        if isinstance(event.source, SourceGroup):
            group_id = event.source.group_id
            try:
                line_bot_api.reply_message(reply_token, TextSendMessage(text="👋 Leaving this group as requested."))
                line_bot_api.leave_group(group_id)
                app.logger.info(f"Bot left group: {group_id}")
            except Exception as e:
                app.logger.error(f"Error leaving group {group_id}: {e}")
                line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ Failed to leave group: {e}"))
        elif isinstance(event.source, SourceRoom):
            room_id = event.source.room_id
            try:
                line_bot_api.reply_message(reply_token, TextSendMessage(text="👋 Leaving this room as requested."))
                line_bot_api.leave_room(room_id)
                app.logger.info(f"Bot left room: {room_id}")
            except Exception as e:
                app.logger.error(f"Error leaving room {room_id}: {e}")
                line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ Failed to leave room: {e}"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="This command can only be used in a group or multi-person chat."))

    elif text.startswith("/list_admins"):
        admins = get_all_admins_from_db()
        if admins:
            admin_list_text = "Current Admins:\n" + "\n".join(admins)
        else:
            admin_list_text = "No additional admins registered."
        line_bot_api.reply_message(reply_token, TextSendMessage(text=admin_list_text))

    elif text.startswith("/mod"):
        line_bot_api.reply_message(reply_token, TextSendMessage(text="🛡️ Mod feature coming soon! (Placeholder)"))

    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="🤖 Unknown command. Try /ping, /leave_group, or /list_admins."))

if __name__ == "__main__":
    # This part is for local testing.
    # In a production environment (like when deployed to a server),
    # you'd typically use a WSGI server like Gunicorn.
    # For local testing, you might need to use ngrok to expose your
    # local Flask app to the internet and set the ngrok URL as your
    # LINE webhook URL.
    app.run(port=5000)
