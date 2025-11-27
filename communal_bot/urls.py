# communal_bot/urls.py
from django.urls import path
from bot.views import telegram_webhook

urlpatterns = [
    path('webhook/', telegram_webhook, name='telegram_webhook'),
]