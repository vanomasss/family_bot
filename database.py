import sqlite3

DB_NAME = "reminders.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Создаём таблицу, если её нет
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            remind_time TEXT,
            repeat_type TEXT DEFAULT 'once',
            created_by INTEGER,
            is_sent INTEGER DEFAULT 0
        )
    """)
    
    # Пробуем добавить колонку repeat_type, если её ещё нет (для старых баз)
    try:
        cur.execute("ALTER TABLE reminders ADD COLUMN repeat_type TEXT DEFAULT 'once'")
    except sqlite3.OperationalError:
        # Колонка уже существует — ничего не делаем
        pass
    
    conn.commit()
    conn.close()

def add_reminder(user_id, text, remind_time, repeat_type, created_by):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (user_id, text, remind_time, repeat_type, created_by) VALUES (?, ?, ?, ?, ?)",
        (user_id, text, remind_time, repeat_type, created_by)
    )
    conn.commit()
    conn.close()

def get_reminders(user_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT id, text, remind_time, repeat_type FROM reminders WHERE user_id = ? AND is_sent = 0", (user_id,))
    else:
        cur.execute("SELECT id, user_id, text, remind_time, repeat_type FROM reminders WHERE is_sent = 0")
    data = cur.fetchall()
    conn.close()
    return data

def get_today_reminders(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, text, remind_time FROM reminders 
        WHERE user_id = ? AND is_sent = 0 AND remind_time LIKE date('now') || '%'
    """, (user_id,))
    data = cur.fetchall()
    conn.close()
    return data

def delete_reminder(reminder_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def mark_as_sent(reminder_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
