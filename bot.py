# bot.py
import asyncio
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

TOKEN = "8531331166:AAEsQZ9SXtTa2r21axUqdAXq8mJ7z9x4_MM"
WEBAPP_URL = "https://bright-peony-7d7f91.netlify.app"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# FastAPI для лидерборда
api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД
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

# ============ ТЕЛЕГРАМ-БОТ ============

@dp.message(lambda msg: msg.text == "/start")
async def start_cmd(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(
            text="🪐 ASTROTAP",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]],
        resize_keyboard=True
    )
    await msg.answer("🚀 Добро пожаловать в AstroTap!\nТапай, качай апгрейды, соревнуйся!", reply_markup=kb)

@dp.message(lambda msg: msg.web_app_data is not None)
async def web_app_data(msg: types.Message):
    try:
        data = int(msg.web_app_data.data)
        user_id = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or "unknown"

        async with aiosqlite.connect("users.db") as db:
            # Проверяем текущий баланс
            cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            current_balance = row[0] if row else 0

            # Сохраняем только если новый баланс больше
            if data > current_balance:
                await db.execute(
                    "INSERT OR REPLACE INTO users (user_id, balance, username) VALUES (?, ?, ?)",
                    (user_id, data, username)
                )
                await db.commit()
                await msg.answer(f"✅ Сохранено! У тебя {data} 💎")
            else:
                await msg.answer(f"📊 Уже сохранено {current_balance} 💎 (локально: {data})")

    except Exception as e:
        await msg.answer(f"Ошибка: {e}")

# ============ API ДЛЯ ЛИДЕРБОРДА ============

@api.get("/leaderboard")
async def leaderboard():
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute(
            "SELECT username, balance FROM users ORDER BY balance DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
    
    result = [{"username": row[0], "balance": row[1]} for row in rows]
    return {"leaderboard": result}

@api.get("/rank/{user_id}")
async def get_rank(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            balance = row[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE balance > ?", (balance,)
            )
            rank_row = await cursor.fetchone()
            rank = rank_row[0] + 1
            return {"rank": rank, "balance": balance}
        else:
            return {"rank": None, "balance": 0}

# ============ ЗАПУСК ============

async def main():
    await init_db()
    
    # Запускаем polling бота в фоне
    asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем FastAPI сервер
    config = uvicorn.Config(api, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())