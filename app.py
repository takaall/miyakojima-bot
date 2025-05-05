# app.py (アプリケーションファクトリパターン)
import os
from flask import Flask, request, abort

# --- LINE Bot SDK のインポート ---
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError

# --- ★注意：ここでは app = Flask(__name__) を書かない！ ---

# --- イベント処理関数を定義 ---
# この関数は create_app の中でハンドラに登録される
def handle_message(event, line_bot_api): # line_bot_api を受け取るように変更（ApiClientの管理のため）
    user_message = event.message.text
    reply_text = "ふむふむ（ファクトリ版）。まだ勉強中じゃ。" # 応答メッセージを少し変えて区別

    # 元のメッセージ分岐ロジック
    if user_message in ["おはよう", "こんにちは", "こんばんは"]:
        reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。（ファクトリ版）"
    elif user_message == "天気":
         reply_text = "宮古島の天気（ファクトリ版）。鋭意準備中！"
    elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
         reply_text = "面白い話（ファクトリ版）。仕入れ中！"

    try:
        # 受け取った line_bot_api インスタンスを使って返信
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
        print(f"Replied (factory): {user_message}")
    except Exception as e:
        print(f"Reply Error (factory): {e}")

# --- アプリケーションファクトリ関数 ---
def create_app():
    # ★この関数の中で Flask アプリケーションを作成・設定する
    app = Flask(__name__)
    app.logger.info("Flask app created inside factory.")

    # 環境変数を読み込む
    line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

    if not line_channel_access_token or not line_channel_secret:
        app.logger.critical("CRITICAL ERROR: Missing environment variables in factory.")
        # エラー発生時はアプリを返さずに終了させるなど考慮が必要
        raise RuntimeError("Missing LINE environment variables") # エラーを発生させて Vercel に伝える

    # ★LINE SDKコンポーネントもファクトリ関数の中で初期化
    try:
        configuration = Configuration(access_token=line_channel_access_token)
        handler = WebhookHandler(line_channel_secret)
        app.logger.info("LINE SDK initialized inside factory.")

        # ★ハンドラ関数を登録 (ApiClient の管理方法に注意)
        # ApiClient はリクエストごとに生成・破棄するのが安全な場合がある
        # ここではコールバック内で都度生成する想定で登録
        @handler.add(MessageEvent, message=TextMessageContent)
        def handle_message_wrapper(event):
             with ApiClient(configuration) as api_client:
                 line_bot_api = MessagingApi(api_client)
                 handle_message(event, line_bot_api) # 元の処理関数を呼び出す

        app.logger.info("Message handler registered inside factory.")

    except Exception as e:
        app.logger.critical(f"CRITICAL ERROR: Failed to initialize LINE SDK in factory: {e}")
        raise RuntimeError(f"Failed to initialize LINE SDK: {e}") # エラーを発生させる

    # ★ルート定義もファクトリ関数の中で行う
    @app.route("/")
    def hello_world():
        # 簡単なステータス表示
        handler_status = "OK" if 'handler' in locals() and handler is not None else "FAIL"
        config_status = "OK" if 'configuration' in locals() and configuration is not None else "FAIL"
        return f"Factory Bot Running! Handler: {handler_status}, Config: {config_status}"

    @app.route("/callback", methods=['POST'])
    def callback():
        # このスコープでは handler が初期化されているはず (失敗時は起動時にエラーになるため)
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        app.logger.info("Request body: " + body)
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            print("Invalid signature.")
            abort(400)
        except Exception as e:
           print(f"Webhook handling error: {e}")
           app.logger.error(f"Webhook handling error: {e}")
           abort(500)
        return 'OK'

    app.logger.info("Routes defined inside factory.")
    # ★設定済みの Flask アプリインスタンスを返す
    return app

# --- 重要 ---
# ファイルのトップレベルには 'app = Flask(...)' を書かない！
# Vercel は 'create_app' という名前の関数を自動で見つけて実行してくれるはずです。
# (vercel.json の設定は通常変更不要)