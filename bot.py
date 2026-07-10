# bot.py
import asyncio
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.filters import Command
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
import json
import aiosqlite

TOKEN = "8531331166:AAFjqwWfhyUK8ATb42Bz81Wp1FfBf9bvgpc"
WEBAPP_URL = "https://bright-peony-7d7f91.netlify.app"
ADMIN_ID = 8683532059

bot = Bot(token=TOKEN)
dp = Dispatcher()

api = FastAPI()
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

awaiting_broadcast = {}

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                username TEXT
            )
        """)
        await db.commit()

# ============ /start ============
@dp.message(lambda msg: msg.text == "/start")
async def start_cmd(msg: types.Message):
    # Сохраняем username при старте
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name or "unknown"
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, balance, username) VALUES (?, 0, ?)",
            (user_id, username)
        )
        # Обновляем username если он изменился
        await db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id)
        )
        await db.commit()
    
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🪐 ASTROTAP", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await msg.answer(
        "🚀 *ДОБРО ПОЖАЛОВАТЬ В ASTROTAP!*\n\n"
        "Привет, космонавт! Первая космическая тапалка в Telegram.\n\n"
        "🪐 *Что тебя ждёт:*\n"
        "• Тапай по планете — очки сохраняются *автоматически*!\n"
        "• 8 апгрейдов до 10 уровней\n"
        "• Таблица лидеров\n"
        "• Вампиризм, щит, комбо, удача\n\n"
        "📢 Канал: @AstroTap\n\n"
        "Жми кнопку и погнали! 👇",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ============ Сохранение (тихое) ============
@dp.message(lambda msg: msg.web_app_data is not None)
async def web_app_data(msg: types.Message):
    try:
        data = int(msg.web_app_data.data)
        user_id = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or "unknown"
        async with aiosqlite.connect("users.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, balance, username) VALUES (?, ?, ?)",
                (user_id, data, username)
            )
            await db.commit()
    except:
        pass

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("🚫 Нет доступа.")
        return
    await msg.answer(
        "🛸 *АДМИН-ПАНЕЛЬ ASTROTAP*\n\n"
        "📢 `/broadcast` — рассылка всем игрокам\n"
        "📊 `/stats` — статистика\n"
        "💎 `/give ID сумма` — начислить очки\n"
        "👤 `/user ID` — инфо об игроке\n"
        "🆔 `/myid` — узнать свой ID",
        parse_mode="Markdown"
    )

@dp.message(Command("myid"))
async def myid_cmd(msg: types.Message):
    await msg.answer(f"🆔 Твой ID: `{msg.from_user.id}`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_start(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    awaiting_broadcast[msg.from_user.id] = True
    await msg.answer("📢 Отправь текст для рассылки.\nПоддерживается *Markdown*\n/cancel — отмена", parse_mode="Markdown")

@dp.message(Command("cancel"))
async def cancel_cmd(msg: types.Message):
    if msg.from_user.id in awaiting_broadcast:
        del awaiting_broadcast[msg.from_user.id]
        await msg.answer("❌ Рассылка отменена.")

@dp.message(lambda msg: msg.from_user.id in awaiting_broadcast)
async def broadcast_send(msg: types.Message):
    if msg.text.startswith('/'): return
    del awaiting_broadcast[msg.from_user.id]
    
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()
    
    sent, failed = 0, 0
    await msg.answer(f"📢 Рассылка на {len(users)} чел...")
    
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, f"📢 *ОБНОВЛЕНИЕ ASTROTAP*\n\n{msg.text}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await msg.answer(f"✅ Готово!\n📬 Отправлено: {sent}\n❌ Не доставлено: {failed}")

@dp.message(Command("stats"))
async def stats_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT COUNT(*), SUM(balance), MAX(balance) FROM users")
        row = await cursor.fetchone()
    await msg.answer(
        f"📊 *СТАТИСТИКА*\n\n👥 Игроков: {row[0]}\n💎 Всего очков: {row[1] or 0}\n🏆 Рекорд: {row[2] or 0}",
        parse_mode="Markdown"
    )

@dp.message(Command("give"))
async def give_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("/give [ID] [сумма]")
        return
    try:
        target_id, amount = int(parts[1]), int(parts[2])
    except:
        await msg.answer("❌ /give 123456 1000")
        return
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (target_id, amount, "admin_gift"))
        await db.commit()
    await msg.answer(f"✅ {amount} 💎 → {target_id}")
    try:
        await bot.send_message(target_id, f"🎁 Администратор начислил вам {amount} 💎!")
    except:
        pass

@dp.message(Command("user"))
async def user_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("/user [ID]")
        return
    try:
        target_id = int(parts[1])
    except:
        await msg.answer("❌ Неверный ID")
        return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance, username FROM users WHERE user_id = ?", (target_id,))
        row = await cursor.fetchone()
    if row:
        await msg.answer(f"👤 {row[1]}\n🆔 {target_id}\n💎 {row[0]}")
    else:
        await msg.answer("❌ Пользователь не найден.")

# ============ API ============

@api.post("/save")
async def save_balance(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        balance = data.get("balance")
        username = data.get("username", "unknown")
        
        # Если user_id нет — сохраняем с username
        if balance is not None:
            async with aiosqlite.connect("users.db") as db:
                if user_id:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, balance, username) VALUES (?, ?, ?)",
                        (user_id, balance, username)
                    )
                else:
                    # Сохраняем по username
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, balance, username) VALUES (?, ?, ?)",
                        (hash(username) % 1000000000, balance, username)
                    )
                await db.commit()
            return {"status": "ok"}
    except Exception as e:
        print("Save error:", e)
    return {"status": "error"}

@api.get("/leaderboard")
async def leaderboard():
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 100")
        rows = await cursor.fetchall()
    return {"leaderboard": [{"username": r[0], "balance": r[1]} for r in rows]}

@api.get("/rank/{user_id}")
async def get_rank(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (row[0],))
            rank_row = await cursor.fetchone()
            return {"rank": rank_row[0] + 1, "balance": row[0]}
        return {"rank": None, "balance": 0}

async def main():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
    config = uvicorn.Config(api, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
