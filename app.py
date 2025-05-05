from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    # ルートURLにアクセスしたら単純な文字を返す
    return "Hello World from Minimal Flask!"

@app.route('/callback')
def callback_stub():
    # LINEからのアクセス(Webhook検証)用に/callbackパスだけ残しておく
    # 正常を示すステータスコード 200 と 'OK' を返す
    return 'OK', 200

# LINE Bot SDK関連のimportや設定、処理は全て削除