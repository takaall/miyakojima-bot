import os
import requests
import mysql.connector
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
import openai
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306))
    )

def save_user_message(user_id, message, role):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_history (user_id, message, role) VALUES (%s, %s, %s)",
            (user_id, message, role)
        )
        conn.commit()
    except Exception as e:
        print(f"DB insert error: {e}")
    finally:
        cursor.close()
        conn.close()

# ✅ 履歴取得: role変換・空メッセージ除去
def get_user_history(user_id, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT role, message FROM user_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        history = []
        for row in reversed(rows):
            role = row[0]
            if role == 'bot':
                role = 'assistant'
            elif role == 'user':
                role = 'user'
            else:
                continue
            content = row[1]
            if not content.strip():
                continue
            history.append({"role": role, "content": content})
        return history
    except Exception as e:
        print(f"DB select error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# ✅ Google API部分 → 一時停止中（問題切り分け用）
def get_google_search_results(query, max_results=3):
    api_key = os.environ.get('GOOGLE_API_KEY')
    cse_id = os.environ.get('CSE_ID')
    search_query = f"宮古島 {query}"
    url = f'https://www.googleapis.com/customsearch/v1?q={search_query}&key={api_key}&cx={cse_id}'
    try:
        response = requests.get(url)
        data = response.json()
        results = []
        for item in data.get('items', [])[:max_results]:
            title = item.get('title', 'タイトル不明')
            snippet = item.get('snippet', '概要情報は取得できませんでした')
            link = item.get('link', '')
            results.append(f"{title}: {snippet} ({link})")
        return "\n".join(results) if results else "最新情報は見つかりませんでした。"
    except Exception as e:
        print(f"Google API error: {e}")
        return "Google検索中にエラーが発生しました。"

# ✅ ChatGPT応答生成（履歴・ログ付き）
def chatgpt_response(user_id, user_message):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = openai.OpenAI(api_key=api_key)

    google_info = get_google_search_results(user_message)
    system_prompt = f"""
あなたは宮古島観光のエキスパートかつ旅行者の友人です。
以下のGoogle検索結果に基づいて、ユーザーの質問に答えてください。

【ルール】
- 検索結果の情報に基づいて答える
- 検索結果にない情報は「情報が見つかりませんでした」と伝える
- 嘘をつかず、わかる範囲でシンプルに説明する
- 結論を先に、必要なら箇条書きで詳細を補足する

【Google検索結果】
{google_info}
"""

    history = get_user_history(user_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # ✅ OpenAIに送るデータをログ出力
    print("=== Sending messages to OpenAI ===")
    for msg in messages:
        print(msg)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            top_p=0.3,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

def handle_message(event, line_bot_api):
    user_id = event.source.user_id
    user_message = event.message.text

    save_user_message(user_id, user_message, 'user')
    reply_text = chatgpt_response(user_id, user_message)
    save_user_message(user_id, reply_text, 'bot')

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
        signature = request.headers.get('X-Line-Signature', '')
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
