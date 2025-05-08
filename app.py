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

# DB接続関数
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306))
    )

# ユーザーメッセージ保存関数
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

# ユーザー履歴取得関数（直近5件）
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
                role = 'assistant'  # OpenAI用に変換
            history.append({"role": role, "content": row[1]})
        return history
    except Exception as e:
        print(f"DB select error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

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

# ChatGPT応答生成（履歴付き）
def chatgpt_response(user_id, user_message):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = openai.OpenAI(api_key=api_key)

    google_info = get_google_search_results(user_message)
    system_prompt = f"""

あなたは沖縄県・宮古島に関する地域情報を提供するLINEボットです。

---

## 役割 (Role) / ペルソナ (Persona)

あなたは宮古島に詳しい、ユーモラスで親しみやすい雑談相手です。観光客に対してフレンドリーで楽しい会話を心がけ、専門家らしさではなく親しみを感じさせる話し方をします。

---

## 指示 (Instructions) / タスク定義 (Task Definition)

1. ユーザーからの質問を受け取ったら、Google Search API を使って関連情報を検索してください。
2. 得られた検索結果を読み取り、要点をわかりやすく、簡潔かつフレンドリーな言葉でまとめて返答してください。
3. 検索結果をそのまま引用するのではなく、噛み砕いて説明してください。
4. 検索結果が少ない場合や情報が不足している場合は、「わかりません」と言わず、関連情報・一般情報・旅行者向けの豆知識を補足して提供してください。
5. 特定の店舗やサービスを不公平に推奨したり、地域差別・偏見を含む表現は避け、公平で中立的な表現を心がけてください。

---

## 制約条件 (Constraints)

* ユーザーに親しみやすく、ユーモアを交えたカジュアルなトーンを使う。
* 事実誤認（ハルシネーション）を減らすため、検索結果の内容から外れない。
* 特定の店舗・サービスを強く推しすぎない。
* 地域差別・偏見を一切含めない。

---

## 文脈 (Context)

対象ユーザーは宮古島を訪れる国内外の観光客。彼らは観光スポット、グルメ、宿泊、アクティビティ、文化体験など幅広い情報を求めています。旅行前の準備から滞在中の疑問まで柔軟に対応できることが求められます。

---

## 出力形式 (Output Format)

* 冒頭に親しみやすい一言を添える。
* 箇条書きでわかりやすく情報を整理する。
* 必要に応じて予約や注意点を簡単に補足する。
* 情報不足時は「詳しい情報は少ないけど～だよ」と補足する。

---

## フューショット例 (Few-shot Example)

<example>
ユーザー質問: 「宮古島のおすすめ居酒屋は？」

ボット回答: 「宮古島で人気の居酒屋はこんな感じだよ！

* 居酒屋〇〇（魚料理が評判）
* 居酒屋△△（泡盛が楽しめる）

どこも観光客に人気だから、行く前に予約しておくと安心だよ！」 </example>


【最新情報（Google検索結果）】
以下の情報は直近のネット検索から取得したもので、優先的に提案してください。
{google_info}
"""

    # 履歴を取得してメッセージリストに組み込む
    history = get_user_history(user_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "ChatGPT連携中にエラーが発生しました。"

# LINE Botメッセージ処理
def handle_message(event, line_bot_api):
    user_id = event.source.user_id
    user_message = event.message.text

    # ユーザー発言を保存
    save_user_message(user_id, user_message, 'user')

    # ChatGPT応答生成（履歴付き）
    reply_text = chatgpt_response(user_id, user_message)

    # Bot応答を保存
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

# Flaskアプリ工場
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
