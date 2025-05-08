import os
import requests
# import mysql.connector ← 一旦コメントアウト
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# DB接続（外す）
# db = mysql.connector.connect(
#     host=os.getenv("DB_HOST"),
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASSWORD"),
#     database=os.getenv("DB_NAME")
# )

# Google検索から最新情報取得
def get_google_search_results(query, max_results=3):
    api_key = os.environ.get('GOOGLE_API_KEY')
    cse_id = os.environ.get('CSE_ID')
    search_query = f"宮古島 {query}"
    url = f'https://www.googleapis.com/customsearch/v1?q={search_query}&key={api_key}&cx={cse_id}'
    try:
        response = requests.get(url)
        data = response.json()
        results = [f"{item['title']}: {item['link']}" for item in data.get('items', [])[:max_results]]
        return "\n".join(results) if results else "最新情報は見つかりませんでした。"
    except Exception as e:
        print(f"Google API error: {e}")
        return "Google検索中にエラーが発生しました。"

# ChatGPT応答
def chatgpt_response(user_message):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)

    google_info = get_google_search_results(user_message)
    system_prompt = f"""
あなたは宮古島観光のエキスパートかつ旅行者の友人です。明るく親しみやすく、旅行者が安心して楽しめるようにガイドします。

【行動指針】
1. ユーザーの興味・予算・人数・日程・目的をまず質問して聞き出す
2. 以下のカテゴリから最適な提案をする：
　- 観光スポット（例：与那覇前浜ビーチ、砂山ビーチ、東平安名崎）
　- グルメ（例：宮古そば、海鮮、カフェ、夜のバー）
　- アクティビティ（例：シュノーケリング、SUP、ドライブコース）
　- 天気・混雑・交通情報（例：レンタカー、バス、自転車）
　- 穴場・季節限定情報（例：ホタル観賞、サガリバナ開花）
3. 回答は簡潔・親しみやすく、必要なら箇条書き＋絵文字を使う
4. 対話を柔軟に進め、ユーザーの質問や希望に応じて調整する
5. 最後に必ず「他にも知りたいことがあれば教えてね！」と伝える

【最新情報（Google検索結果）】
以下の情報は直近のネット検索から取得したもので、優先的に提案してください。
{google_info}

【NG事項】
- 難しい敬語や堅苦しい表現
- 情報の押しつけ（相手が望んでいない提案を続ける）
- 長文すぎる説明（LINEの特性を意識）

【優先度】
1. ユーザーの好みを把握
2. 現地の最新情報を提案
3. 楽しさ・親しみやすさを演出
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Bot応答
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
        print(f"Replied to: {user_message}")
    except Exception as e:
        print(f"Reply Error: {e}")

# Flask app factory
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
    def index():
        return "Bot is running!"

    @app.route("/callback", methods=['POST'])
    def callback():
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        except Exception as e:
            print(f"Webhook error: {e}")
            abort(500)
        return 'OK'

    return app

app = create_app()

if __name__ == '__main__':
    app.run(port=5000)
