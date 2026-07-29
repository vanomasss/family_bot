from flask import Flask
from threading import Thread
from main import main

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_bot():
    import asyncio
    asyncio.run(main())

Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)