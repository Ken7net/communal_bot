from django.db import models
from django.core.validators import MinValueValidator

class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Utility(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20, default="ед.")

class Tariff(models.Model):
    utility = models.ForeignKey(Utility, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=10, decimal_places=4)
    valid_from = models.DateTimeField()

    class Meta:
        ordering = ['-valid_from']

class MeterReading(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    utility = models.ForeignKey(Utility, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    timestamp = models.DateTimeField()
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'utility', 'timestamp')

class Charge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    utility = models.ForeignKey(Utility, on_delete=models.CASCADE)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    consumption = models.DecimalField(max_digits=12, decimal_places=3)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'utility', 'period_end')

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    timestamp = models.DateTimeField()
    comment = models.TextField(blank=True)

class FSMState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    state_name = models.CharField(max_length=100)
    context = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)