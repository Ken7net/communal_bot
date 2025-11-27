"""
ASGI config for communal_bot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more details, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'communal_bot.settings')

application = get_asgi_application()