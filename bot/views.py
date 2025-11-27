# bot/views.py
import json
import asyncio
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from telegram import Update
from telegram.ext import Application
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

async def _handle_webhook(update_data):
    """Полный асинхронный цикл обработки обновления."""
    update = Update.de_json(update_data, bot=None)
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    await app.initialize()
    try:
        await app.process_update(update)
    finally:
        await app.shutdown()

@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        update_data = json.loads(request.body.decode('utf-8'))
        # Единственный вызов asyncio.run()
        asyncio.run(_handle_webhook(update_data))
        return HttpResponse('OK')
    except Exception as e:
        logger.exception("Webhook failed")
        return HttpResponse('Error', status=500)