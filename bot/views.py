import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from telegram import Update
from telegram.ext import Application
from django.conf import settings
import asyncio

@csrf_exempt
@require_POST
def telegram_webhook(request):
    update_data = json.loads(request.body.decode("utf-8"))
    update = Update.de_json(update_data, bot=None)
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    asyncio.run(app.update_queue.put(update))
    asyncio.run(app.process_update(update))
    
    return HttpResponse('OK')