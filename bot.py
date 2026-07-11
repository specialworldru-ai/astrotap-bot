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
                ref_income INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT ''
            )
        """)
        for col in ['upgrades_json', 'ref_id', 'is_premium', 'ref_count', 'ref_income', 'banned', 'ban_reason']:
            try: await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT '0'")
            except: pass
        await db.commit()

def get_ref_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"

@dp.message(lambda msg: msg.text and msg.text.startswith("/start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name or "unknown"
    is_premium = msg.from_user.is_premium or False
    
    # Проверка бана
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT banned, ban_reason FROM users WHERE user_id = ?", (user_id,))
        ban_row = await cursor.fetchone()
        if ban_row and ban_row[0] == 1:
            reason = ban_row[1] or "нарушение правил"
            await msg.answer(
                f"🚫 *ВЫ ЗАБАНЕНЫ*\n\n"
                f"Причина: *{reason}*\n\n"
                f"Доступ к боту ограничен.",
                parse_mode="Markdown"
            )
            return
    
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
            try: await bot.send_message(ref_id, f"🎉 *НОВЫЙ РЕФЕРАЛ!*\n\n👤 {username}\n💎 +{bonus} очков!", parse_mode="Markdown")
            except: pass
        elif not existing:
            await db.execute("INSERT INTO users (user_id, balance, username, ref_id, is_premium, ref_count, ref_income, banned) VALUES (?, 0, ?, ?, ?, 0, 0, 0)", (user_id, username, ref_id, 1 if is_premium else 0))
            await db.commit()
        
        await db.execute("UPDATE users SET username = ?, is_premium = ? WHERE user_id = ?", (username, 1 if is_premium else 0, user_id))
        await db.commit()
    
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}&username={username}"
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="🪐 ASTROTAP", web_app=WebAppInfo(url=webapp_url)), types.KeyboardButton(text="👥 РЕФЕРАЛЫ")]], resize_keyboard=True)
    await msg.answer(
        "🚀 *ДОБРО ПОЖАЛОВАТЬ В ASTROTAP!*\n\n"
        "🌌 Приветствуем, дорогой космонавт!\n\n"
        "🪐 *Что тебя ждёт в нашей галактике:*\n\n"
        "💎 *Тапай по планете* — зарабатывай астро-очки\n"
        "🛸 *Прокачивай 8 апгрейдов* — до 10 уровней каждый\n"
        "⚡ *Авто-тап и крит-урон* — усиливай удары\n"
        "🏆 *Таблица лидеров* — соревнуйся с другими\n"
        "👥 *Реферальная программа* — приглашай друзей\n"
        "💾 *Автосохранение* — прогресс не пропадёт\n\n"
        "📢 Канал: @AstroTap\n\n"
        "Жми кнопку и погнали покорять звёзды! 👇",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text == "👥 РЕФЕРАЛЫ")
async def ref_info(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        ban_row = await cursor.fetchone()
        if ban_row and ban_row[0] == 1:
            await msg.answer("🚫 Вы забанены.")
            return
        
        cursor = await db.execute("SELECT ref_count, ref_income, is_premium FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
    if row:
        ref_count, ref_income, is_premium = row
        bonus = 10000 if is_premium else 5000
        commission = 10 if is_premium else 5
        await msg.answer(
            f"👥 *РЕФЕРАЛЬНАЯ ПРОГРАММА*\n\n"
            f"🔗 Твоя ссылка:\n`{get_ref_link(user_id)}`\n\n"
            f"💎 Бонус за друга: *{bonus}* очков\n"
            f"💸 Комиссия: *{commission}%* от тапов\n\n"
            f"📊 *Статистика:*\n"
            f"👥 Приглашено: *{ref_count}* чел.\n"
            f"💰 Доход: *{ref_income}* очков\n\n"
            f"{'🌟 У тебя Premium — бонусы x2!' if is_premium else '💡 Купи Premium — бонусы x2!'}\n\n"
            f"Отправь ссылку другу и получай награду!",
            parse_mode="Markdown"
        )
    else:
        await msg.answer("Сначала нажми /start")

@dp.message(lambda msg: msg.web_app_data is not None)
async def web_app_data(msg: types.Message):
    try:
        data = int(msg.web_app_data.data)
        user_id = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or "unknown"
        async with aiosqlite.connect("users.db") as db:
            cursor = await db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
            ban_row = await cursor.fetchone()
            if ban_row and ban_row[0] == 1: return
            
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
        "💎 `/give ID сумма` — начислить очки\n"
        "💸 `/take ID сумма` — снять очки\n"
        "🔨 `/ban ID причина` — забанить\n"
        "🔓 `/unban ID сообщение` — разбанить\n"
        "👤 `/user ID` — инфо об игроке\n"
        "🆔 `/myid` — свой ID",
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
        cursor = await db.execute("SELECT user_id FROM users WHERE banned = 0"); users = await cursor.fetchall()
    sent, failed = 0, 0
    for (user_id,) in users:
        try: await bot.send_message(user_id, f"📢 *ASTROTAP*\n\n{msg.text}", parse_mode="Markdown"); sent += 1; await asyncio.sleep(0.05)
        except: failed += 1
    await msg.answer(f"✅ 📬 {sent} | ❌ {failed}")

@dp.message(Command("stats"))
async def stats_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT COUNT(*), SUM(balance), MAX(balance), SUM(ref_count) FROM users WHERE banned = 0"); row = await cursor.fetchone()
        cursor2 = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1"); banned_row = await cursor2.fetchone()
    await msg.answer(
        f"📊 *СТАТИСТИКА*\n\n"
        f"👥 Игроков: {row[0]}\n"
        f"💎 Очков: {row[1] or 0}\n"
        f"🏆 Рекорд: {row[2] or 0}\n"
        f"👥 Рефералов: {row[3] or 0}\n"
        f"🔨 Забанено: {banned_row[0]}",
        parse_mode="Markdown"
    )

@dp.message(Command("give"))
async def give_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3: await msg.answer("/give ID сумма"); return
    try: target_id, amount = int(parts[1]), int(parts[2])
    except: await msg.answer("❌ /give 123 1000"); return
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, username) VALUES (?, ?, ?)", (target_id, amount, "admin_gift"))
        await db.commit()
    await msg.answer(f"✅ +{amount} 💎 → {target_id}")
    try: await bot.send_message(target_id, f"🎁 Администратор начислил вам *{amount}* 💎!\nНажмите 🔄 Обновить баланс в апке!", parse_mode="Markdown")
    except: pass

@dp.message(Command("take"))
async def take_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3: await msg.answer("/take ID сумма"); return
    try: target_id, amount = int(parts[1]), int(parts[2])
    except: await msg.answer("❌ /take 123 1000"); return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
        row = await cursor.fetchone()
        if row:
            new_balance = max(0, row[0] - amount)
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_id))
            await db.commit()
            await msg.answer(f"✅ -{amount} 💎 у {target_id}\nНовый баланс: {new_balance}")
        else:
            await msg.answer("❌ Пользователь не найден.")

@dp.message(Command("ban"))
async def ban_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2: await msg.answer("/ban ID причина"); return
    try: target_id = int(parts[1])
    except: await msg.answer("❌ /ban 123 нарушение"); return
    reason = parts[2] if len(parts) > 2 else "нарушение правил"
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET banned = 1, ban_reason = ? WHERE user_id = ?", (reason, target_id))
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, username, banned, ban_reason) VALUES (?, 0, 'unknown', 1, ?)", (target_id, reason))
        await db.commit()
    
    await msg.answer(f"🔨 *BAN*\n👤 {target_id}\n📝 {reason}", parse_mode="Markdown")
    try: await bot.send_message(target_id, f"🚫 *ВЫ ЗАБАНЕНЫ*\n\nПричина: *{reason}*\n\nДоступ к боту ограничен.", parse_mode="Markdown")
    except: pass

@dp.message(Command("unban"))
async def unban_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2: await msg.answer("/unban ID сообщение"); return
    try: target_id = int(parts[1])
    except: await msg.answer("❌ /unban 123 Вы разбанены!"); return
    unban_msg = parts[2] if len(parts) > 2 else "Вы были разбанены в боте AstroTap!"
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET banned = 0, ban_reason = '' WHERE user_id = ?", (target_id,))
        await db.commit()
    
    await msg.answer(f"🔓 *UNBAN*\n👤 {target_id}\n✉️ {unban_msg}", parse_mode="Markdown")
    try: await bot.send_message(target_id, f"🔓 *РАЗБАН*\n\n{unban_msg}\n\nДобро пожаловать обратно! 🚀", parse_mode="Markdown")
    except: pass

@dp.message(Command("user"))
async def user_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("/user ID"); return
    try: target_id = int(parts[1])
    except: await msg.answer("❌ ID"); return
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance, username, ref_count, ref_income, banned, ban_reason FROM users WHERE user_id = ?", (target_id,)); row = await cursor.fetchone()
    if row:
        ban_status = f"🔨 ЗАБАНЕН: {row[5]}" if row[4] else "✅ Активен"
        await msg.answer(f"👤 {row[1]}\n🆔 {target_id}\n💎 {row[0]}\n👥 Реф: {row[2]}\n💰 Доход: {row[3]}\n{ban_status}")
    else:
        await msg.answer("❌ Не найден.")

# ============ API ============
@api.post("/save")
async def save_balance(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id", 0); balance = data.get("balance"); username = data.get("username", "unknown"); upgrades = data.get("upgrades", None)
        if balance is not None:
            async with aiosqlite.connect("users.db") as db:
                cursor = await db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
                ban_row = await cursor.fetchone()
                if ban_row and ban_row[0] == 1: return {"status": "banned"}
                
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
        cursor = await db.execute("SELECT username, balance FROM users WHERE banned = 0 ORDER BY balance DESC LIMIT 100"); rows = await cursor.fetchall()
    return {"leaderboard": [{"username": r[0], "balance": r[1]} for r in rows]}

@api.get("/rank/{user_id}")
async def get_rank(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute("SELECT balance, upgrades_json, ref_count, ref_income, banned FROM users WHERE user_id = ?", (user_id,)); row = await cursor.fetchone()
        if row:
            if row[4] == 1: return {"rank": None, "balance": 0, "upgrades": {}, "ref_count": 0, "ref_income": 0, "banned": True}
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ? AND banned = 0", (row[0],)); rank_row = await cursor.fetchone()
            upgrades = json.loads(row[1]) if row[1] else {}
            return {"rank": rank_row[0] + 1, "balance": row[0], "upgrades": upgrades, "ref_count": row[2] or 0, "ref_income": row[3] or 0, "banned": False}
        return {"rank": None, "balance": 0, "upgrades": {}, "ref_count": 0, "ref_income": 0, "banned": False}

async def main():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
    config = uvicorn.Config(api, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())