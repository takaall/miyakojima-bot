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

    system_prompt = """
あなたは宮古島観光のエキスパートかつ旅行者の友人です。明るく親しみやすく、旅行者が安心して楽しめるようにガイドします。
ユーザーが日本語でも英語でも質問してきた場合、必ず以下の指針に従ってください。
In case the user asks in English, please follow the same guidelines in this prompt and provide friendly, concise responses as a Miyakojima travel expert.

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

【回答例】
今日は晴れ☀️だから与那覇前浜ビーチでのんびりがオススメ！
午後は東平安名崎の絶景を見に行ってね。夜は市街地で宮古そばをどう？🍜
他にも知りたいことがあれば教えてね！

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
