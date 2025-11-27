# bot/telegram_bot.py
import os
import asyncio
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from django.conf import settings
from bot.handlers import (
    start, submit_reading, add_payment, balance,
    add_utility, set_tariff, delete_utility, delete_tariff,
    list_utilities, list_tariffs,
    list_users, user_balance,
    admin_submit_reading, admin_add_payment,
    handle_callback, handle_message
)

class Command(BaseCommand):
    help = "Run Telegram bot with webhook"

    def handle(self, *args, **options):
        asyncio.run(self.run_bot())

    async def run_bot(self):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Регистрация всех обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("submit_reading", submit_reading))
        app.add_handler(CommandHandler("add_payment", add_payment))
        app.add_handler(CommandHandler("balance", balance))
        app.add_handler(CommandHandler("add_utility", add_utility))
        app.add_handler(CommandHandler("set_tariff", set_tariff))
        app.add_handler(CommandHandler("delete_utility", delete_utility))
        app.add_handler(CommandHandler("delete_tariff", delete_tariff))
        app.add_handler(CommandHandler("list_utilities", list_utilities))
        app.add_handler(CommandHandler("list_tariffs", list_tariffs))
        app.add_handler(CommandHandler("list_users", list_users))
        app.add_handler(CommandHandler("user_balance", user_balance))
        app.add_handler(CommandHandler("admin_submit_reading", admin_submit_reading))
        app.add_handler(CommandHandler("admin_add_payment", admin_add_payment))

        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
        if not webhook_url:
            raise ValueError("RENDER_EXTERNAL_URL must be set")

        self.stdout.write(f"Setting webhook to {webhook_url}/webhook/")
        await app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            webhook_url=f"{webhook_url}/webhook/",
            secret_token=None,
        )