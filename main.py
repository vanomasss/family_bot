import os
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN, FAMILY_IDS, FAMILY_NAMES, DAILY_REMIND_TIME
from database import init_db, add_reminder, get_reminders, delete_reminder, mark_as_sent, get_today_reminders

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


class ReminderState(StatesGroup):
    choosing_recipient = State()
    entering_text = State()
    entering_date = State()
    entering_time = State()
    choosing_repeat = State()


def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Создать напоминание", callback_data="create")],
        [InlineKeyboardButton(text="📋 Мои напоминания", callback_data="my_reminders")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Все напоминания", callback_data="all_reminders")]
    ])


def recipient_menu():
    buttons = []
    for name, uid in FAMILY_IDS.items():
        buttons.append([InlineKeyboardButton(text=f"👤 {name.capitalize()}", callback_data=f"user_{uid}")])
    buttons.append([InlineKeyboardButton(text="👨‍👩‍👧‍👦 Всем", callback_data="user_all")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quick_date_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="date_today")],
        [InlineKeyboardButton(text="📅 Завтра", callback_data="date_tomorrow")],
        [InlineKeyboardButton(text="⌨️ Ввести дату вручную (ДД.ММ)", callback_data="date_manual")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])


def repeat_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Один раз", callback_data="repeat_once")],
        [InlineKeyboardButton(text="🔁 Каждый день", callback_data="repeat_daily")],
        [InlineKeyboardButton(text="🔁 Каждую неделю", callback_data="repeat_weekly")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        f"🌟 Привет, {message.from_user.first_name}!\n\n"
        f"Я — семейный напоминалка. Помогаю не забывать о важном! 📌\n\n"
        f"Выбери действие ниже ⬇️",
        reply_markup=main_menu()
    )


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "back":
        await state.clear()
        await callback.message.edit_text(
            "🌟 Главное меню:",
            reply_markup=main_menu()
        )
        await callback.answer()
        return

    if data == "create":
        await state.set_state(ReminderState.choosing_recipient)
        await callback.message.edit_text(
            "👤 Кому напомнить?",
            reply_markup=recipient_menu()
        )
        await callback.answer()
        return

    if data.startswith("user_"):
        recipient = data.replace("user_", "")
        await state.update_data(recipient=recipient)
        await state.set_state(ReminderState.entering_text)
        await callback.message.edit_text(
            "✍️ Напиши текст напоминания:",
            reply_markup=back_button()
        )
        await callback.answer()
        return

    if data == "my_reminders":
        user_id = callback.from_user.id
        reminders = get_reminders(user_id)
        if not reminders:
            await callback.message.edit_text(
                "📭 У тебя нет активных напоминаний",
                reply_markup=main_menu()
            )
        else:
            text = "📋 Твои напоминания:\n\n"
            keyboard = []
            for r in reminders:
                repeat_emoji = {"once": "🔹", "daily": "🔄", "weekly": "📆"}.get(r[3], "🔹")
                text += f"{repeat_emoji} #{r[0]} | {r[1]} (до {r[2]})\n"
                keyboard.append([InlineKeyboardButton(
                    text=f"❌ Удалить #{r[0]}",
                    callback_data=f"delete_{r[0]}"
                )])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        await callback.answer()
        return

    if data == "all_reminders":
        reminders = get_reminders()
        if not reminders:
            await callback.message.edit_text(
                "📭 Нет активных напоминаний",
                reply_markup=main_menu()
            )
        else:
            text = "👨‍👩‍👧‍👦 Все напоминания:\n\n"
            keyboard = []
            for r in reminders:
                name = FAMILY_NAMES.get(r[1], "Всем") if r[1] else "Всем"
                repeat_emoji = {"once": "🔹", "daily": "🔄", "weekly": "📆"}.get(r[4], "🔹")
                text += f"{repeat_emoji} #{r[0]} | {name}: {r[2]} (на {r[3]})\n"
                keyboard.append([InlineKeyboardButton(
                    text=f"❌ Удалить #{r[0]}",
                    callback_data=f"delete_{r[0]}"
                )])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        await callback.answer()
        return

    if data.startswith("delete_"):
        rem_id = int(data.replace("delete_", ""))
        delete_reminder(rem_id)
        await callback.message.edit_text(
            "✅ Напоминание удалено!",
            reply_markup=main_menu()
        )
        await callback.answer()
        return

    if data.startswith("date_"):
        now = datetime.now()
        if data == "date_today":
            target_date = now.date()
        elif data == "date_tomorrow":
            target_date = (now + timedelta(days=1)).date()
        else:
            await callback.message.edit_text(
                "⌨️ Введи дату в формате **ДД.ММ** (например, 15.08) или **ГГГГ-ММ-ДД**:",
                parse_mode="Markdown",
                reply_markup=back_button()
            )
            await callback.answer()
            return

        await state.update_data(target_date=target_date.strftime("%Y-%m-%d"))
        await state.set_state(ReminderState.entering_time)
        await callback.message.edit_text(
            "⏰ Теперь введи время в формате **ЧЧ:ММ** (например, 14:30):",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        await callback.answer()
        return

    if data.startswith("repeat_"):
        repeat_type = data.replace("repeat_", "")
        await state.update_data(repeat_type=repeat_type)
        await save_reminder(callback, state)
        await callback.answer()
        return


@dp.message(ReminderState.entering_text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(ReminderState.entering_date)
    await message.answer(
        "📅 На какую дату поставить напоминание?",
        reply_markup=quick_date_menu()
    )


@dp.message(ReminderState.entering_date)
async def process_date_manual(message: types.Message, state: FSMContext):
    text = message.text.strip()
    now = datetime.now()
    target_date = None

    for fmt in ("%d.%m", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            year = parsed.year if parsed.year > 1900 else now.year
            target_date = datetime(year, parsed.month, parsed.day).date()
            break
        except ValueError:
            continue

    if not target_date:
        await message.answer(
            "❌ Неверный формат даты. Попробуй еще раз (например, 15.08):",
            reply_markup=back_button()
        )
        return

    await state.update_data(target_date=target_date.strftime("%Y-%m-%d"))
    await state.set_state(ReminderState.entering_time)
    await message.answer(
        "⏰ Теперь введи время в формате **ЧЧ:ММ** (например, 14:30):",
        parse_mode="Markdown",
        reply_markup=back_button()
    )


@dp.message(ReminderState.entering_time)
async def process_time(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%H:%M")
        data = await state.get_data()
        target_date_str = data.get("target_date")
        
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        remind_time = datetime(target_date.year, target_date.month, target_date.day, dt.hour, dt.minute)

        await state.update_data(remind_time=remind_time.strftime("%Y-%m-%d %H:%M"))
        await state.set_state(ReminderState.choosing_repeat)
        await message.answer(
            "🔄 Как часто напоминать?",
            reply_markup=repeat_menu()
        )
    except Exception:
        await message.answer(
            "❌ Неправильный формат времени. Напиши ЧЧ:ММ (например, 14:30)",
            reply_markup=back_button()
        )


async def save_reminder(event, state):
    data = await state.get_data()
    recipient = data.get("recipient")
    text = data.get("text")
    remind_time = data.get("remind_time")
    repeat_type = data.get("repeat_type", "once")

    user_id = None if recipient == "all" else int(recipient)
    created_by = event.from_user.id

    add_reminder(user_id, text, remind_time, repeat_type, created_by)
    await state.clear()

    repeat_emoji = {"once": "однократное", "daily": "ежедневное", "weekly": "еженедельное"}.get(repeat_type, "однократное")
    repeat_icon = {"once": "🔹", "daily": "🔄", "weekly": "📆"}.get(repeat_type, "🔹")

    if user_id:
        name = FAMILY_NAMES.get(user_id, "Неизвестно")
        msg = f"✅ Напоминание для {name} создано!\n\n📝 {text}\n⏰ {remind_time}\n{repeat_icon} Повтор: {repeat_emoji}"
    else:
        msg = f"✅ Напоминание для всех создано!\n\n📝 {text}\n⏰ {remind_time}\n{repeat_icon} Повтор: {repeat_emoji}"

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(msg, reply_markup=main_menu())
    else:
        await event.answer(msg, reply_markup=main_menu())


async def send_daily_reminders():
    """Ежедневная утренняя рассылка в личные сообщения в 08:00"""
    for user_id in FAMILY_IDS.values():
        reminders = get_today_reminders(user_id)
        if reminders:
            text = "☀️ Доброе утро! Сегодня у тебя запланировано:\n\n"
            for r in reminders:
                text += f"🔔 {r[1]} (в {r[2].split()[1]})\n"
            await bot.send_message(user_id, text)
        else:
            await bot.send_message(user_id, "☀️ Доброе утро! На сегодня дел нет. Отдыхай! 😊")


async def check_reminders():
    """Проверка и отправка сработавших напоминаний в личку"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    reminders = get_reminders()

    for r in reminders:
        rem_id, user_id, text, remind_time, repeat_type = r

        if remind_time <= now:
            if user_id is None:
                for uid in FAMILY_IDS.values():
                    await bot.send_message(uid, f"⏰ НАПОМИНАНИЕ ВСЕМ:\n\n{text}")
            else:
                await bot.send_message(user_id, f"⏰ НАПОМИНАНИЕ:\n\n{text}")

            conn = sqlite3.connect("reminders.db")
            cur = conn.cursor()

            if repeat_type == "once":
                mark_as_sent(rem_id)
            elif repeat_type == "daily":
                new_time = (datetime.strptime(remind_time, "%Y-%m-%d %H:%M") + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
                cur.execute("UPDATE reminders SET remind_time = ?, is_sent = 0 WHERE id = ?", (new_time, rem_id))
                conn.commit()
            elif repeat_type == "weekly":
                new_time = (datetime.strptime(remind_time, "%Y-%m-%d %H:%M") + timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M")
                cur.execute("UPDATE reminders SET remind_time = ?, is_sent = 0 WHERE id = ?", (new_time, rem_id))
                conn.commit()

            conn.close()


# --- ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Фейковый веб-сервер запущен на порту {port}")


# --- ГЛАВНАЯ ТОЧКА ВХОДА ---
async def main():
    init_db()

    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.add_job(send_daily_reminders, "cron", hour=8, minute=0)
    scheduler.start()

    await start_web_server()

    print("🌟 Бот запущен!")
    print(f"⏰ Ежедневная рассылка в {DAILY_REMIND_TIME}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
