import os
from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
# ↓↓↓ここから修正・追加↓↓↓
from linebot.v3.webhooks import (
    MessageEvent,           # <<< これを追加！
    TextMessageContent,     # <<< これを追加！
    WebhookHandler
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
# ↑↑↑ここまで修正・追加↑↑↑

app = Flask(__name__)

# 環境変数からアクセストークンとチャネルシークレットを取得
# 重要：これらは Vercel 上で設定します！
configuration = Configuration(access_token=os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# ルートURLへのアクセス確認用（任意）
@app.route("/")
def hello_world():
    return "Hello from Your Bot!"

# LINEからのWebhookを受け取るルート
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers['X-Line-Signature']

    # リクエストボディを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 署名を検証し、問題なければhandleに定義されている関数を呼び出す
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/secret.")
        abort(400)
    except Exception as e:
        print(f"Error occurred: {e}")
        abort(500)

    return 'OK'

# テキストメッセージを受け取ったときの処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_message = event.message.text # ユーザーが送ったメッセージ

        reply_text = "ふむふむ、我が主。今はまだ勉強中でございます。" # デフォルトの返信

        # 挨拶への応答
        if user_message in ["おはよう", "こんにちは", "こんばんは"]:
            reply_text = f"{user_message}、我が主！ ご機嫌麗しゅう。"
        # 「天気」への応答（準備中）
        elif user_message == "天気":
            # ユーザーの現在地は宮古島であるため、宮古島に関する情報を返すように設定
            # (これはDay 3以降に天気APIと連携する想定)
             reply_text = "宮古島の天気ですな？ すぐにお知らせできるよう鋭意準備中でございます！ しばしお待ちを！"
        # 「雑学」「豆知識」などへの応答（準備中 - ChatGPT連携予定）
        elif user_message in ["雑学", "豆知識", "面白い話", "なんか話して"]:
            reply_text = "おお、知的好奇心ですな！ 面白い情報を仕入れてまいります故、今しばらくお待ちくださいませ！"

        # メッセージを返信する
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


# # アプリケーションを実行 (ローカルテスト用)
# if __name__ == "__main__":
#     # ポート番号は Vercel が自動で設定するため、ローカルでの実行時のみ指定
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port, debug=True) # debug=True は開発中のみ