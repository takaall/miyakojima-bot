import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ChatGPT 応答関数
def chatgpt_response(user_message):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=300,
            temperature=0.7,
        )
        reply_text = response.choices[0].message.content.strip()
        return reply_text
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Bot 応答関数
def handle_message(event, line_bot_api):
    user_message = event.message.text

    if user_message in ["おはよう", "こんにちは", "こんばんは"]:
        reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。（ファクトリ版）"
    elif user_message == "天気":
        reply_text = "宮古島の天気（ファクトリ版）。鋭意準備中！"
    elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
        reply_text = "面白い話（ファクトリ版）。仕入れ中！"
    else:
        reply_text = chatgpt_response(user_message)

    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
        print(f"Replied (factory): {user_message}")
    except Exception as e:
        print(f"Reply Error (factory): {e}")

# アプリケーションファクトリ関数
def create_app():
    app = Flask(__name__)
    app.logger.info("Flask app created inside factory.")

    line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

    if not line_channel_access_token or not line_channel_secret:
        app.logger.critical("CRITICAL ERROR: Missing environment variables in factory.")
        raise RuntimeError("Missing LINE environment variables")

    try:
        configuration = Configuration(access_token=line_channel_access_token)
        handler = WebhookHandler(line_channel_secret)
        app.logger.info("LINE SDK initialized inside factory.")

        @handler.add(MessageEvent, message=TextMessageContent)
        def handle_message_wrapper(event):
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                handle_message(event, line_bot_api)

        app.logger.info("Message handler registered inside factory.")

    except Exception as e:
        app.logger.critical(f"CRITICAL ERROR: Failed to initialize LINE SDK in factory: {e}")
        raise RuntimeError(f"Failed to initialize LINE SDK: {e}")

    @app.route("/")
    def hello_world():
        handler_status = "OK" if 'handler' in locals() and handler is not None else "FAIL"
        config_status = "OK" if 'configuration' in locals() and configuration is not None else "FAIL"
        return f"ファクトリーボット実行中！ハンドラー: {handler_status}、構成: {config_status}"

    @app.route("/callback", methods=['POST'])
    def callback():
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
    return app

# Vercel 用
app = create_app()

# ローカル実行用
if __name__ == '__main__':
    app.run(port=5000)
