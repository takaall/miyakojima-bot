import os
from flask import Flask, request, abort

# --- Corrected Imports ---
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
# --- End Imports ---

app = Flask(__name__)

# --- Initialization with Environment Variables ---
line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

if not line_channel_access_token:
    print("CRITICAL ERROR: LINE_CHANNEL_ACCESS_TOKEN environment variable not set.")
if not line_channel_secret:
    print("CRITICAL ERROR: LINE_CHANNEL_SECRET environment variable not set.")

# --- Initialize LINE Bot SDK components ---
configuration = None
handler = None # ★ まずNoneで初期化

# Configuration の初期化
if line_channel_access_token:
    try:
        configuration = Configuration(access_token=line_channel_access_token)
        print("LINE Configuration initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize LINE Configuration: {e}")
else:
     print("CRITICAL ERROR: Cannot initialize LINE Configuration due to missing access token.")

# WebhookHandler の初期化
if line_channel_secret:
    try:
        handler = WebhookHandler(line_channel_secret) # ★ ここでインスタンス化
        print("LINE WebhookHandler initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize LINE WebhookHandler: {e}")
else:
     print("CRITICAL ERROR: Cannot initialize LINE WebhookHandler due to missing secret.")


# --- Routes ---
@app.route("/")
def hello_world():
    status = "Ready (Handler Initialized)" if handler else "Ready (Handler FAILED Initialization)"
    config_status = "OK" if configuration else "FAILED"
    return f"Hello from Miyakojima Bot! Handler Status: {status}, Config Status: {config_status}"

@app.route("/callback", methods=['POST'])
def callback():
    if not handler: # ★ ハンドラが初期化失敗していたら処理中断
        print("Error: WebhookHandler not initialized during callback.")
        abort(500)

    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature) # ★ 初期化済みのハンドラを使用
    except InvalidSignatureError:
        print("Invalid signature.")
        abort(400)
    except Exception as e:
       print(f"Error occurred during webhook handling: {e}")
       abort(500)

    return 'OK'

# --- Event Handler FUNCTION ---
# ★注意: ここでは @handler.add デコレータを使わない！★
# 関数として定義するだけ。
def handle_message(event):
    if not configuration: # ★ Configurationが初期化失敗していたら処理中断
        print("Error: Configuration not initialized during message handling.")
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_message = event.message.text
        reply_text = "ふむふむ、我が主。今はまだ勉強中でございます。"

        # (元のコードにあったメッセージ分岐処理 ... 省略)
        if user_message in ["おはよう", "こんにちは", "こんばんは"]:
            reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。"
        elif user_message == "天気":
             reply_text = "宮古島の天気ですな？ すぐにお知らせできるよう鋭意準備中でございます！ しばしお待ちを！"
        elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
             reply_text = "おお、知的好奇心ですな！ 面白い情報を仕入れてまいります故、今しばらくお待ちくださいませ！"

        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            print(f"Replied to user message: {user_message}")
        except Exception as e:
            print(f"Error occurred trying to reply to user: {e}")

# --- ★ ハンドラ関数を手動で登録 ---
# WebhookHandlerの初期化が成功した場合にのみ実行
if handler:
    try:
        # handler インスタンスの .add() メソッドを直接呼び出す
        handler.add(MessageEvent, message=TextMessageContent)(handle_message)
        print("Message handler registered successfully.")
    except Exception as e:
        # 登録に失敗した場合（通常は起こらないはずだが念のため）
        print(f"CRITICAL ERROR: Failed to register message handler: {e}")
else:
    # handlerがNoneのままの場合（初期化に失敗した場合）
    print("WARNING: WebhookHandler not initialized. Message handler cannot be registered.")

# --- Optional: Local execution block ---
# if __name__ == "__main__":
#    ... (省略) ...