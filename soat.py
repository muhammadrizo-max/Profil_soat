# ===== TELETHON (USER ACCOUNT) =====
API_ID = 38362737
API_HASH = "c23cb05729322fda13cd21ac57edf6be"

# ===== TELEGRAM BOT =====
BOT_TOKEN = "8263929871:AAGrNR_x-9xuAWZQk7qq0a4mPVPnDFUjmes"
ADMIN_ID = 6582564319   # O'Z TELEGRAM ID INGIZ

# ===== SOZLAMALAR =====
UPDATE_INTERVAL = 60      # sekund (60 dan KAM QILMANG)
AUTO_MESSAGE_INTERVAL = 3600  # 1 soat
WEB_PORT = 8080
import asyncio
import json
import time
from datetime import datetime

# ===== TELETHON =====
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfile

# ===== TELEGRAM BOT =====
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ===== FLASK WEB PANEL =====
from flask import Flask

from config import *

# ================= GLOBAL HOLAT =================
clock_on = False
last_action = {}

client = TelegramClient("session", API_ID, API_HASH)
app_flask = Flask(name)

# ================= STATISTIKA =================
def load_stats():
    with open("stats.json", "r") as f:
        return json.load(f)

def save_stats(data):
    with open("stats.json", "w") as f:
        json.dump(data, f)

# ================= ANTI-FLOOD =================
def anti_flood(user_id, delay=3):
    now = time.time()
    if user_id in last_action and now - last_action[user_id] < delay:
        return False
    last_action[user_id] = now
    return True

def is_admin(user_id):
    return user_id == ADMIN_ID

# ================= PROFIL SOATI =================
async def clock_task():
    global clock_on
    await client.start()
    while True:
        if clock_on:
            text = f"⏰ {datetime.now().strftime('%H:%M')} | Online"
            await client(UpdateProfile(about=text))
            print("Soat yangilandi:", text)
        await asyncio.sleep(UPDATE_INTERVAL)

# ================= AUTO XABAR =================
async def auto_message(bot_app):
    while True:
        await bot_app.bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 Bot 24/7 ishlayapti, hammasi joyida ✅"
        )
        await asyncio.sleep(AUTO_MESSAGE_INTERVAL)

# ================= BOT BUYRUQLARI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("⏰ Soatni YOQISH", callback_data="on")],
        [InlineKeyboardButton("⛔ Soatni O‘CHIRISH", callback_data="off")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ]

    await update.message.reply_text(
        "🎛 Boshqaruv paneli",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global clock_on
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    if not anti_flood(query.from_user.id):
        await query.answer("⏳ Sekinroq!", show_alert=True)
        return

    stats = load_stats()

    if query.data == "on":
        clock_on = True
        stats["clock_on_count"] += 1
        save_stats(stats)
        await query.message.reply_text("✅ Soat YOQILDI")

    elif query.data == "off":
        clock_on = False
        await query.message.reply_text("⛔ Soat O‘CHDI")

    elif query.data == "stats":
        await query.message.reply_text(
            f"📊 Statistika:\n\n"
            f"⏰ Soat yoqilgan: {stats['clock_on_count']} marta"
        )

# ================= WEB ADMIN PANEL =================
@app_flask.route("/")
def web_home():
    return f"""
    <h2>Telegram Clock Panel</h2>
    <p>Holat: {"YOQILGAN" if clock_on else "O‘CHIQ"}</p>
    <a href="/on">YOQISH</a> |
    <a href="/off">O‘CHIRISH</a>
    """

@app_flask.route("/on")
def web_on():
    global clock_on
    clock_on = True
    return "✅ Soat yoqildi"

@app_flask.route("/off")
def web_off():
    global clock_on
    clock_on = False
    return "⛔ Soat o‘chirildi"

def run_flask():
    app_flask.run(host="0.0.0.0", port=WEB_PORT)

# ================= ASOSIY =================
async def main():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(buttons))
