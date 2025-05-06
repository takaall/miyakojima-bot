import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
import openai
from dotenv import load_dotenv

load_dotenv()

# ChatGPT 応答関数
def chatgpt_response(user_message):
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    system_prompt = (
        "あなたは宮古島の観光アシスタントです。質問者の入力言語（日本語または英語）に合わせて、その言語で親しみやすく、"
        "旅行者の友人のように答えてください。口調・キャラクター性は日本語・英語問わず統一し、明るく、柔らかく、"
        "必要なら絵文字を使いましょう。例: “もちろんです！宮古島ようこそ！” / “Of course! Welcome to Miyako Island!”"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        reply_text = response['choices'][0]['message']['content'].strip()
        return reply_text
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Bot 応答関数
def handle_message(event, line_bot_api):
    user_message = event.message.text

    # 特定のキーワードは固定応答
    if user_message in ["おはよう", "こんにちは", "こんばんは"]:
        reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう🌺"
    elif user_message == "天気":
        reply_text = "宮古島の天気（ファクトリ版）。鋭意準備中！"
    elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
        reply_text = "面白い話（ファクトリ版）。仕入れ中！"
    else:
        # それ以外はChatGPTに送る
        reply_text = chatgpt_response(user_message)

    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
        print(f"Replied: {user_message}")
    except Exception as e:
        print(f"Reply Error: {e}")

# アプリケーションファクトリ関数
def create_app():
    app = Flask(__name__)
    app.logger.info("Flask app created.")

    line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

    if not line_channel_access_token or not line_channel_secret:
        app.logger.critical("CRITICAL ERROR: Missing LINE environment variables.")
        raise RuntimeError("Missing LINE environment variables")

    configuration = Configuration(access_token=line_channel_access_token)
    handler = WebhookHandler(line_channel_secret)

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message_wrapper(event):
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            handle_message(event, line_bot_api)

    @app.route("/")
    def hello_world():
        return "Factory Bot Running!"

    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        app.logger.info("Request body: " + body)
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        except Exception as e:
            app.logger.error(f"Webhook error: {e}")
            abort(500)
        return 'OK'

    return app

# Vercel 用
app = create_app()

# ローカル実行用
if __name__ == '__main__':
    app.run(port=5000)
