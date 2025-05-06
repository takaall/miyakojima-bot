import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import openai

load_dotenv()

# ChatGPT応答関数
def chatgpt_response(user_message):
    system_prompt = (
        "あなたは宮古島観光のエキスパートかつ旅行者の友人です。明るく親しみやすく、旅行者が安心して楽しめるようにガイドします。"
        "日本語と英語の両方で対応できます。英語でも同じフレンドリーなトーン、親しみやすさ、絵文字の使い方を心がけてください。"
        "フォーマルすぎる表現は避け、旅行者に寄り添う会話をしてください。"
    )
    try:
        client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.5,
        )
        reply_text = response.choices[0].message.content.strip()
        return reply_text
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Bot応答関数
def handle_message(event, line_bot_api):
    user_message = event.message.text
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

# Flaskアプリ作成
def create_app():
    app = Flask(__name__)
    line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

    if not line_channel_access_token or not line_channel_secret:
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
        return "Miyakojima Bot Running!"

    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        except Exception as e:
            abort(500)
        return 'OK'

    return app

app = create_app()

if __name__ == '__main__':
    app.run(port=5000)
