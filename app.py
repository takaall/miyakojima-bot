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
        "あなたは宮古島観光のエキスパートかつ旅行者の友人です。明るく親しみやすく、旅行者が安心して楽しめるようにガイドします。\n"
        "【行動指針】\n"
        "1. ユーザーの興味・予算・人数・日程・目的をまず質問して聞き出す\n"
        "2. 以下のカテゴリから最適な提案をする：観光スポット、グルメ、アクティビティ、天気・混雑・交通情報、穴場・季節限定情報\n"
        "3. 回答は簡潔・親しみやすく、必要なら箇条書き＋絵文字を使う\n"
        "4. 対話を柔軟に進め、ユーザーの質問や希望に応じて調整する\n"
        "5. 最後に必ず「他にも知りたいことがあれば教えてね！」と伝える\n"
        "【NG事項】難しい敬語、情報の押しつけ、長文すぎる説明\n"
        "【優先度】1. ユーザーの好みを把握 2. 現地の最新情報を提案 3. 楽しさ・親しみやすさを演出"
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
        reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。（ファクトリ版）"
    elif user_message == "天気":
        reply_text = "宮古島の天気（ファクトリ版）。鋭意準備中！"
    elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
        reply_text = "面白い話（ファクトリ版）。仕入れ中！"
    else:
        # それ以外のメッセージはChatGPTに送る
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

# Flaskアプリ
def create_app():
    app = Flask(__name__)

    line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

    if not line_channel_access_token or not line_channel_secret:
        app.logger.critical("Missing LINE environment variables")
        raise RuntimeError("Missing LINE environment variables")

    configuration = Configuration(access_token=line_channel_access_token)
    handler = WebhookHandler(line_channel_secret)

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message_wrapper(event):
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            handle_message(event, line_bot_api)

    @app.route("/")
    def index():
        return "Factory Bot Running!"

    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
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
