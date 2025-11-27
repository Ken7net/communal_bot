from django.db import transaction
from decimal import Decimal
from .models import MeterReading, Charge, Tariff

def calculate_and_create_charge(user, utility, new_reading_value, new_timestamp):
    last_reading = MeterReading.objects.filter(
        user=user, utility=utility, is_confirmed=True
    ).order_by('-timestamp').first()

    if not last_reading:
        return None
    if new_reading_value < last_reading.value:
        raise ValueError("Показания не могут уменьшаться")

    consumption = new_reading_value - last_reading.value
    if consumption == 0:
        return None

    tariff = Tariff.objects.filter(
        utility=utility, valid_from__lte=new_timestamp
    ).order_by('-valid_from').first()

    if not tariff:
        raise ValueError("Тариф не задан")

    amount = (consumption * tariff.rate).quantize(Decimal('0.01'))

    with transaction.atomic():
        Charge.objects.create(
            user=user,
            utility=utility,
            period_start=last_reading.timestamp,
            period_end=new_timestamp,
            consumption=consumption,
            amount=amount
        )
        MeterReading.objects.create(
            user=user,
            utility=utility,
            value=new_reading_value,
            timestamp=new_timestamp,
            is_confirmed=True
        )
    return True