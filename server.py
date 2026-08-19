import os
import time
import requests
import threading
from flask import Flask
import config

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Earning Elevated Bot Engine - 24/7 Active"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    while True:
        time.sleep(300)
        try:
            requests.get(config.RENDER_APP_URL)
        except Exception:
            pass

def start_server():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
