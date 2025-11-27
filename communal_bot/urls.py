# communal_bot/urls.py
from django.http import HttpResponse
from django.urls import path

urlpatterns = [
    path('', lambda r: HttpResponse("Bot is running via telegram_bot command")),
]