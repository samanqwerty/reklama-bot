import asyncio
import logging
import json
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# ============================================================
# SOZLAMALAR - Railway da Environment Variables orqali o'rnatiladi
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
REKLAMA_MATNI = os.environ.get("REKLAMA_MATNI", "Bu reklama matni. Railway da o'zgartiring!")
INTERVAL_MINUTES = int(os.environ.get("INTERVAL_MINUTES", "15"))
GROUPS_FILE = "groups.json"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# GURUHLARNI SAQLASH / YUKLASH
# ============================================================

def load_groups() -> set:
    try:
        with open(GROUPS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_groups(groups: set):
    with open(GROUPS_FILE, "w") as f:
        json.dump(list(groups), f)

active_groups: set = load_groups()

# ============================================================
# REKLAMA YUBORISH
# ============================================================

async def send_reklama(context: ContextTypes.DEFAULT_TYPE):
    if not active_groups:
        logger.info("Hozircha guruh yo'q.")
        return

    dead = set()
    for chat_id in active_groups.copy():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=REKLAMA_MATNI,
                parse_mode="HTML"
            )
            logger.info(f"✅ Yuborildi: {chat_id}")
        except TelegramError as e:
            logger.warning(f"❌ Yuborib bo'lmadi {chat_id}: {e}")
            dead.add(chat_id)

    if dead:
        active_groups -= dead
        save_groups(active_groups)

# ============================================================
# BOT GURUHGA QO'SHILGANDA
# ============================================================

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            chat_id = update.effective_chat.id
            chat_title = update.effective_chat.title or "Noma'lum guruh"
            active_groups.add(chat_id)
            save_groups(active_groups)
            logger.info(f"🆕 Yangi guruh: {chat_title} ({chat_id})")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Reklama bot faollashdi!\n⏱ Har {INTERVAL_MINUTES} daqiqada reklama yuboriladi."
            )

# ============================================================
# BOT GURUHDAN CHIQARILGANDA
# ============================================================

async def on_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.left_chat_member:
        return

    if update.message.left_chat_member.id == context.bot.id:
        chat_id = update.effective_chat.id
        active_groups.discard(chat_id)
        save_groups(active_groups)
        logger.info(f"🚪 Guruhdan chiqarildi: {chat_id}")

# ============================================================
# ISHGA TUSHIRISH
# ============================================================

async def post_init(application: Application):
    application.job_queue.run_repeating(
        send_reklama,
        interval=INTERVAL_MINUTES * 60,
        first=10  # 10 soniyadan keyin birinchi yuborish
    )
    logger.info(f"🚀 Bot ishga tushdi! Interval: {INTERVAL_MINUTES} daqiqa")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN o'rnatilmagan! Railway > Variables ga qo'shing.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_left_member))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
