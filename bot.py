import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "من ربات برش موزیک هستم 🎵\n"
        "فعلاً برای تست آماده‌ام!"
    )


def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN پیدا نشد!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
