import os
import requests
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Google検索から最新情報を取得する関数
def get_google_search_results(query, max_results=3, site_filter=None):
    api_key = os.environ.get('GOOGLE_API_KEY')
    cse_id = os.environ.get('CSE_ID')
    search_query = f"宮古島 {query}"
    if site_filter:
        search_query += f" site:{site_filter}"
    url = f'https://www.googleapis.com/customsearch/v1?q={search_query}&key={api_key}&cx={cse_id}'
    try:
        response = requests.get(url)
        data = response.json()
        results = []
        for item in data.get('items', [])[:max_results]:
            results.append(f"{item['title']}: {item['link']}")
        return "\n".join(results) if results else "最新情報は見つかりませんでした。"
    except Exception as e:
        print(f"Google API error: {e}")
        return "Google検索中にエラーが発生しました。"

# ChatGPT 応答関数
def chatgpt_response(user_message, mode="chatgpt"):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    google_info = get_google_search_results(user_message)

    if mode == "direct":  # Google検索結果だけを直接返すモード
        return f"宮古島の最新情報はこちらです:\n{google_info}"

    system_prompt = f"""
あなたはGoogle検索結果の要約専門家です。
以下のGoogle検索結果からのみ情報を抜き出し、推測・想像・創作は禁止です。
検索結果がない場合は「現在の情報は見つかりませんでした」と答えてください。

【Google検索結果】
{google_info}

【重要】
- 検索結果のみを基に回答
- 事実ベースで簡潔に回答
- 必要なら箇条書き・絵文字を使用
- 最後に「他にも知りたいことがあれば教えてね！」と添える
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.2,  # 創作抑制
        )
        reply_text = response.choices[0].message.content.strip()
        return reply_text
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Bot 応答関数
def handle_message(event, line_bot_api):
    user_message = event.message.text

    # mode切り替え例：「直接モード」にしたい場合は"direct"
    reply_text = chatgpt_response(user_message, mode="chatgpt")

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
