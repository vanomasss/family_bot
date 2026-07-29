from flask import Flask
from main import main
import asyncio
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_bot():
    """Запускаем бота в отдельном потоке, но без конфликтов сигналов"""
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка бота: {e}")

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask для поддержки жизни на Render
    app.run(host="0.0.0.0", port=10000)
