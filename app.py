import os
from flask import Flask

app = Flask(__name__)

# 環境変数が Vercel に設定されているか簡単なチェック
line_channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')

@app.route("/")
def hello_world():
    token_status = "セットされています" if line_channel_access_token else "未設定"
    secret_status = "セットされています" if line_channel_secret else "未設定"
    # handler の初期化は行わない
    return f"シンプルなFlaskアプリが動作中！ トークン: {token_status}, シークレット: {secret_status}"

@app.route("/callback", methods=['POST'])
def callback_stub():
    # LINE SDKの処理はせず、単にOKを返す
    print("Callback received (stub)")
    return "OK"

# LINE Bot SDK の初期化や @handler.add はすべて削除する！