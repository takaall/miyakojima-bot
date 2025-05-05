import os
from flask import Flask, request, abort

# --- Corrected Imports ---
# Import core handler component
from linebot.v3 import (
    WebhookHandler
)
# Import webhook event components
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
# Import messaging components
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
# Import exception components
from linebot.v3.exceptions import (
    InvalidSignatureError
)
# --- End Imports ---

app = Flask(__name__)

# --- Initialization with Environment Variables ---
# Get environment variables from Vercel settings
line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

# Basic check if environment variables are set (helps debugging)
if not line_channel_access_token:
    print("CRITICAL ERROR: LINE_CHANNEL_ACCESS_TOKEN environment variable not set.")
    # Optional: You might want the app to intentionally crash or exit here
    # if the token is missing, to make the error obvious in logs.
if not line_channel_secret:
    print("CRITICAL ERROR: LINE_CHANNEL_SECRET environment variable not set.")
    # Optional: Handle missing secret appropriately.

# Initialize LINE Bot SDK components only if secrets are present
configuration = None
handler = None
if line_channel_access_token and line_channel_secret:
    try:
        configuration = Configuration(access_token=line_channel_access_token)
        handler = WebhookHandler(line_channel_secret)
        print("LINE SDK initialized successfully.") # Log success
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize LINE SDK: {e}")
        # App might still run but webhook/reply will fail.
else:
    print("CRITICAL ERROR: Cannot initialize LINE SDK due to missing environment variables.")

# --- Routes ---
# Root route for basic health check
@app.route("/")
def hello_world():
    # Indicate readiness, maybe check if handler is initialized
    status = "Ready (Handler Initialized)" if handler else "Ready (Handler FAILED Initialization)"
    return f"Hello from Miyakojima Bot! Status: {status}"

# Webhook callback route for LINE messages
@app.route("/callback", methods=['POST'])
def callback():
    # Check if handler was initialized successfully
    if not handler:
        print("Error: WebhookHandler not initialized during callback.")
        abort(500) # Internal Server Error

    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # Log the request body for debugging purposes
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/secret.")
        abort(400)
    except Exception as e:
         # Log any other errors during handling
         print(f"Error occurred during webhook handling: {e}")
         abort(500)

    return 'OK'

# --- Event Handlers ---
# Handler for Text Message events
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # Check if configuration was initialized successfully
    if not configuration:
         print("Error: Configuration not initialized during message handling.")
         # Cannot reply without configuration/ApiClient
         return # Exit gracefully

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_message = event.message.text # User's message

        # --- Bot Logic ---
        reply_text = "ふむふむ、我が主。今はまだ勉強中でございます。" # Default reply

        # Respond to greetings
        if user_message in ["おはよう", "こんにちは", "こんばんは"]:
            reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。"
        # Respond to "天気" (Placeholder)
        elif user_message == "天気":
             reply_text = "宮古島の天気ですな？ すぐにお知らせできるよう鋭意準備中でございます！ しばしお待ちを！"
        # Respond to "雑学" etc. (Placeholder)
        elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
            reply_text = "おお、知的好奇心ですな！ 面白い情報を仕入れてまいります故、今しばらくお待ちくださいませ！"
        # --- End Bot Logic ---

        # Send reply message
        try:
             line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
             print(f"Replied to user message: {user_message}") # Log successful reply
        except Exception as e:
             # Log errors during reply attempt
             print(f"Error occurred trying to reply to user: {e}")

# --- Optional: Local execution block (Vercel doesn't use this) ---
# if __name__ == "__main__":
#     # Get port from environment variable or default to 5000
#     port = int(os.environ.get("PORT", 5000))
#     # Enable debug mode for local testing only (provides more detailed errors)
#     # Important: Never run with debug=True in production!
#     app.run(host="0.0.0.0", port=port, debug=False) # Set debug=False for safety