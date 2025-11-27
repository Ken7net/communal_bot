from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from django.conf import settings
from django.core.management.base import BaseCommand
import asyncio
import os

# Импорт всех обработчиков
from bot.handlers import (
    start, submit_reading, add_payment, balance,
    add_utility, set_tariff, delete_utility, delete_tariff,
    list_utilities, list_tariffs,
    list_users, user_balance,
    admin_submit_reading, admin_add_payment,
    handle_callback, handle_message
)

class Command(BaseCommand):
    def handle(self, *args, **options):
        asyncio.run(self.run_bot())

    async def run_bot(self):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Пользовательские команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("submit_reading", submit_reading))
        app.add_handler(CommandHandler("add_payment", add_payment))
        app.add_handler(CommandHandler("balance", balance))

        # Админ: управление
        app.add_handler(CommandHandler("add_utility", add_utility))
        app.add_handler(CommandHandler("set_tariff", set_tariff))
        app.add_handler(CommandHandler("delete_utility", delete_utility))
        app.add_handler(CommandHandler("delete_tariff", delete_tariff))
        app.add_handler(CommandHandler("list_utilities", list_utilities))
        app.add_handler(CommandHandler("list_tariffs", list_tariffs))

        # Админ: данные и ввод от имени
        app.add_handler(CommandHandler("list_users", list_users))
        app.add_handler(CommandHandler("user_balance", user_balance))
        app.add_handler(CommandHandler("admin_submit_reading", admin_submit_reading))
        app.add_handler(CommandHandler("admin_add_payment", admin_add_payment))

        # Общие обработчики
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Webhook
        RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
        if RENDER_EXTERNAL_URL:
            webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/"
            await app.bot.set_webhook(url=webhook_url)
            self.stdout.write(f"Webhook: {webhook_url}")

        await app.initialize()
        await app.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            await app.stop()
            await app.shutdown()