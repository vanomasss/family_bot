from flask import Flask
from main import main
import asyncio

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    import threading
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
    # Запускаем Flask-сервер
    app.run(host="0.0.0.0", port=10000)
