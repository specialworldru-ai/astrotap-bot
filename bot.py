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
WEBAPP_URL = "https://specialworldru-ai.github.io/astrotap-bot/tap.html"
ADMIN_ID = 8683532059
BOT_USERNAME = "AstroTapBot"  # ← ЗАМЕНИ

bot = Bot(token=TOKEN)
dp = Dispatcher()

api = FastAPI()
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

awaiting_broadcast = {}

# Баны
try:
    with open("bans.json", "r") as f:
        banned_users = json.load(f)
except:
    banned_users = {}

def save_bans():
    with open("bans.json", "w") as f:
        json.dump(banned_users, f)

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                username TEXT,
                upgrades_json TEXT DEFAULT '{}',
                ref_id INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                ref_count INTEGER DEFAULT 0,
                ref_income INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at TEXT
            )
        """)
        for col in ['upgrades_json', 'ref_id', 'is_premium', 'ref_count', 'ref_income']:
            try: await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT '0'")
            except: pass
        await db.commit()

def get_ref_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"

# ============ /start ============
@dp.message(lambda msg: msg.text and msg.text.startswith("/start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    
    if str(user_id) in banned_users:
        reason = banned_users[str(user_id)]
        await msg.answer(
            f"🚫 *ВЫ ЗАБАНЕНЫ*\n\nПричина: {reason}\n\nОбратитесь в поддержку: @z9hielove",
            parse_mode="Markdown"
        )
        return
    
    username = msg.from_user.username or msg.from_user.first_name or "unknown"
    is_premium = msg.from_user.is_premium or False
    ref_id = 0
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try: ref_id = int(args[1][3:])
        except: pass
    
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT ref_id FROM users WHERE user_id = ?", (user_id,))
        existing = await cursor.fetchone()
        
        if existing and existing[0] == 0 and ref_id != 0 and ref_id != user_id:
            bonus = 10000 if is_premium else 5000
            await db.execute("UPDATE users SET ref_id = ?, is_premium = ?, balance = balance + ? WHERE user_id = ?", (ref_id, 1 if is_premium else 0, bonus, user_id))
            await db.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
            try: await bot.send_message(ref_id, f"🎉 *Новый реферал!*\n👤 {username}\n💎 +{bonus} очков!", parse_mode="Markdown")
            except: pass
        elif not existing:
            await db.execute("INSERT INTO users (user_id, balance, username, ref_id, is_premium, ref_count, ref_income) VALUES (?, 0, ?, ?, ?, 0, 0)", (user_id, username, ref_id, 1 if is_premium else 0))
            await db.commit()
        
        await db.execute("UPDATE users SET username = ?, is_premium = ? WHERE user_id = ?", (username, 1 if is_premium else 0, user_id))
        await db.commit()
    
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}&username={username}"
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="🪐 ASTROTAP", web_app=WebAppInfo(url=webapp_url)), types.KeyboardButton(text="👥 РЕФЕРАЛЫ")]], resize_keyboard=True)
    await msg.answer(
        "🚀 *ДОБРО ПОЖАЛОВАТЬ В ASTROTAP!*\n\n"
        "Привет, космонавт! Ты попал в первую космическую тапалку в Telegram.\n\n"
        "🪐 *Что тебя ждёт:*\n"
        "• Тапай по планете — очки сохраняются *автоматически*!\n"
        "• Прокачивай 8 апгрейдов до 10 уровней\n"
        "• Соревнуйся в таблице лидеров\n"
        "• Приглашай друзей — получай бонусы\n"
        "• Вампиризм, щит, комбо, удача\n\n"
        "💡 *Совет:* Нажми 🔄 Обновить баланс после начислений!\n\n"
        "📢 Канал: @AstroTap\n\n"
        "Жми кнопку и погнали! 👇",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ============ Кнопка РЕФЕРАЛЫ ============
@dp.message(lambda msg: msg.text == "👥 РЕФЕРАЛЫ")
async def ref_info(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT ref_count, ref_income, is_premium FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
    if row:
        ref_count, ref_income, is_premium = row
        bonus = 10000 if is_premium else 5000
        commission = 10 if is_premium else 5
        await msg.answer(
            f"👥 *РЕФЕРАЛЬНАЯ ПРОГРАММА*\n\n"
            f"🔗 Твоя ссылка:\n`{get_ref_link(user_id)}`\n\n"
            f"💎 Бонус за друга: {bonus} очков\n"
            f"💸 Комиссия: {commission}% от тапов\n\n"
            f"📊 *Статистика:*\n"
            f"👥 Приглашено: {ref_count} чел.\n"
            f"💰 Доход: {ref_income} очков\n\n"
            f"{'🌟 У тебя Telegram Premium — бонусы x2!' if is_premium else '💡 Купи Telegram Premium — бонусы x2!'}",
            parse_mode="Markdown"
        )
    else:
        await msg.answer("Сначала нажми /start")

# ============ Сохранение ============
@dp.message(lambda msg: msg.web_app_data is not None)
async def web_app_data(msg: types.Message):
    try:
        data = int(msg.web_app_data.data)
        user_id = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or "unknown"
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET balance = ?, username = ? WHERE user_id = ?", (data, username, user_id))
            cursor = await db.execute("SELECT ref_id, is_premium FROM users WHERE user_id = ?", (user_id,))
            ref_row = await cursor.fetchone()
            if ref_row and ref_row[0] and ref_row[0] != user_id:
                commission_rate = 0.10 if ref_row[1] else 0.05
                commission = int(data * commission_rate)
                if commission > 0:
                    await db.execute("UPDATE users SET ref_income = ref_income + ?, balance = balance + ? WHERE user_id = ?", (commission, commission, ref_row[0]))
            await db.commit()
    except: pass

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: await msg.answer("🚫 Нет доступа."); return
    await msg.answer(
        "🛸 *АДМИН-ПАНЕЛЬ ASTROTAP*\n\n"
        "📢 `/broadcast` — рассылка\n"
        "📊 `/stats` — статистика\n"
        "💎 `/give ID сумма` — начислить\n"
        "💸 `/removebal ID сумма` — убрать баланс\n"
        "👤 `/user ID` — инфо\n"
        "🚫 `/ban ID причина` — забанить\n"
        "✅ `/unban ID сообщ` — разбанить\n"
        "📋 `/banlist` — список банов",
        parse_mode="Markdown"
    )

@dp.message(Command("myid"))
async def myid_cmd(msg: types.Message):
    await msg.answer(f"🆔 Твой ID: `{msg.from_user.id}`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_start(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    awaiting_broadcast[msg.from_user.id] = True
    await msg.answer("📢 Отправь текст для рассылки.\n/cancel — отмена")

@dp.message(Command("cancel"))
async def cancel_cmd(msg: types.Message):
    if msg.from_user.id in awaiting_broadcast: del awaiting_broadcast[msg.from_user.id]; await msg.answer("❌ Отменено.")

@dp.message(lambda msg: msg.from_user.id in awaiting_broadcast)
async def broadcast_send(msg: types.Message):
    if msg.text.startswith('/'): return
    del awaiting_broadcast[msg.from_user.id]
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT user_id FROM users"); users = await cursor.fetchall()
    sent, failed = 0, 0
    for (user_id,) in users:
        try: await bot.send_message(user_id, f"📢 *ОБНОВЛЕНИЕ ASTROTAP*\n\n{msg.text}", parse_mode="Markdown"); sent += 1; await asyncio.sleep(0.05)
        except: failed += 1
    await msg.answer(f"✅ 📬 {sent} | ❌ {failed}")

@dp.message(Command("stats"))
async def stats_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT COUNT(*), SUM(balance), MAX(balance), SUM(ref_count) FROM users"); row = await cursor.fetchone()
    await msg.answer(f"📊 *СТАТИСТИКА*\n👥 Игроков: {row[0]}\n💎 Очков: {row[1] or 0}\n🏆 Рекорд: {row[2] or 0}\n👥 Реф: {row[3] or 0}\n🚫 Банов: {len(banned_users)}", parse_mode="Markdown")

@dp.message(Command("give"))
async def give_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3: await msg.answer("/give ID сумма"); return
    try: target_id, amount = int(parts[1]), int(parts[2])
    except: await msg.answer("❌ /give 123 1000"); return
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, username) VALUES (?, ?, ?)", (target_id, amount, "admin_gift"))
        await db.commit()
    await msg.answer(f"✅ +{amount} 💎 → {target_id}")
    try: await bot.send_message(target_id, f"🎁 Админ начислил {amount} 💎! Нажми 🔄 Обновить в апке!")
    except: pass

@dp.message(Command("removebal"))
async def removebal_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3: await msg.answer("/removebal ID сумма"); return
    try: target_id, amount = int(parts[1]), int(parts[2])
    except: await msg.answer("❌ /removebal 123 500"); return
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (amount, target_id))
        await db.commit()
    await msg.answer(f"✅ -{amount} 💎 у {target_id}")

@dp.message(Command("user"))
async def user_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("/user ID"); return
    try: target_id = int(parts[1])
    except: await msg.answer("❌ ID"); return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance, username, ref_count, ref_income FROM users WHERE user_id = ?", (target_id,)); row = await cursor.fetchone()
    if row:
        is_banned = str(target_id) in banned_users
        await msg.answer(f"👤 {row[1]}\n🆔 {target_id}\n💎 {row[0]}\n👥 Реф: {row[2]}\n💰 Доход: {row[3]}\n🚫 Бан: {'Да' if is_banned else 'Нет'}")
    else: await msg.answer("❌ Не найден")

# ============ БАНЫ ============
@dp.message(Command("ban"))
async def ban_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3: await msg.answer("/ban ID причина"); return
    try: target_id = int(parts[1]); reason = parts[2]
    except: await msg.answer("❌ /ban 123456 спам"); return
    
    banned_users[str(target_id)] = reason
    save_bans()
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR REPLACE INTO bans (user_id, reason, banned_at) VALUES (?, ?, datetime('now'))", (target_id, reason))
        await db.commit()
    await msg.answer(f"🚫 {target_id} забанен.\nПричина: {reason}")
    try: await bot.send_message(target_id, f"🚫 *ВЫ ЗАБАНЕНЫ*\n\nПричина: {reason}\n\nОбратитесь в поддержку: @z9hielove", parse_mode="Markdown")
    except: pass

@dp.message(Command("unban"))
async def unban_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2: await msg.answer("/unban ID [сообщение]"); return
    try: target_id = int(parts[1]); message = parts[2] if len(parts) > 2 else "Вы были разбанены в боте."
    except: await msg.answer("❌ /unban 123456 Добро пожаловать!"); return
    
    banned_users.pop(str(target_id), None)
    save_bans()
    async with aiosqlite.connect("users.db") as db:
        await db.execute("DELETE FROM bans WHERE user_id = ?", (target_id,))
        await db.commit()
    await msg.answer(f"✅ {target_id} разбанен.")
    try: await bot.send_message(target_id, f"✅ *ВЫ РАЗБАНЕНЫ*\n\n{message}", parse_mode="Markdown")
    except: pass

@dp.message(Command("banlist"))
async def banlist_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    if not banned_users:
        await msg.answer("📋 Список банов пуст.")
        return
    text = "🚫 *ЗАБАНЕНЫ:*\n\n"
    for uid, reason in banned_users.items():
        text += f"🆔 {uid} | {reason}\n"
    await msg.answer(text, parse_mode="Markdown")

# ============ API ============
@api.get("/checkban/{user_id}")
async def check_ban(user_id: int):
    is_banned = str(user_id) in banned_users
    reason = banned_users.get(str(user_id), "")
    return {"banned": is_banned, "reason": reason}

@api.post("/save")
async def save_balance(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id", 0); balance = data.get("balance"); username = data.get("username", "unknown"); upgrades = data.get("upgrades", None)
        if balance is not None:
            async with aiosqlite.connect("users.db") as db:
                if username == "unknown" and user_id:
                    cursor = await db.execute("SELECT username FROM users WHERE user_id = ? AND username != 'unknown'", (user_id,)); row = await cursor.fetchone()
                    if row: username = row[0]
                if upgrades is not None:
                    await db.execute("INSERT OR REPLACE INTO users (user_id, balance, username, upgrades_json) VALUES (?, ?, ?, ?)", (user_id, balance, username, json.dumps(upgrades)))
                else:
                    await db.execute("INSERT OR REPLACE INTO users (user_id, balance, username) VALUES (?, ?, ?)", (user_id, balance, username))
                cursor = await db.execute("SELECT ref_id, is_premium FROM users WHERE user_id = ?", (user_id,)); ref_row = await cursor.fetchone()
                if ref_row and ref_row[0] and ref_row[0] != user_id:
                    commission_rate = 0.10 if ref_row[1] else 0.05; commission = int(balance * commission_rate)
                    if commission > 0: await db.execute("UPDATE users SET ref_income = ref_income + ? WHERE user_id = ?", (commission, ref_row[0]))
                await db.commit()
            return {"status": "ok"}
    except Exception as e: print("Save error:", e)
    return {"status": "error"}

@api.get("/leaderboard")
async def leaderboard():
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 100"); rows = await cursor.fetchall()
    return {"leaderboard": [{"username": r[0], "balance": r[1]} for r in rows]}

@api.get("/rank/{user_id}")
async def get_rank(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance, upgrades_json, ref_count, ref_income FROM users WHERE user_id = ?", (user_id,)); row = await cursor.fetchone()
        if row:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (row[0],)); rank_row = await cursor.fetchone()
            upgrades = json.loads(row[1]) if row[1] else {}
            return {"rank": rank_row[0] + 1, "balance": row[0], "upgrades": upgrades, "ref_count": row[2] or 0, "ref_income": row[3] or 0}
        return {"rank": None, "balance": 0, "upgrades": {}, "ref_count": 0, "ref_income": 0}

async def main():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
    config = uvicorn.Config(api, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())