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

async def _process_update(update):
    """Асинхронная обработка обновления."""
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
        update_data = json.loads(request.body.decode("utf-8"))
        update = Update.de_json(update_data, bot=None)
        # Один вызов asyncio.run() для всего процесса
        asyncio.run(_process_update(update))
        return HttpResponse('OK')
    except Exception as e:
        logger.exception("Critical error in webhook")
        return HttpResponse('Error', status=500)