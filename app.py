from flask import Flask
from main import main
import asyncio
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

if __name__ == "__main__":
    def run_bot():
        asyncio.run(main())
    
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=10000)
