from flask import Flask
from main import main
import asyncio

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке, чтобы Flask отвечал на пинги Render
    import threading
    def run_bot():
        asyncio.run(main())
    
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
