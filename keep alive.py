"""
Renderの「無料Web Service」でBotを動かす場合に使う補助モジュール。

Render無料プランはHTTPポートへのアクセスが一定時間無いとスリープします。
このFlaskサーバーでポートを開いておき、UptimeRobotなどの外部サービスから
定期的にアクセス(ping)することでスリープを防ぎます。

注意:
- これはあくまで無料プランでの回避策です。完全な24/365稼働を保証するものではありません。
- 本番運用や複数サーバーでの利用には、Renderの有料 Background Worker を推奨します。
- main.py 側では使わず、Web Serviceとしてデプロイする場合のみ import してください。
"""
import os
import threading

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running."


def _run():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
