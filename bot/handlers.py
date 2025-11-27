from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .models import User, Utility, Tariff, MeterReading, Charge, Payment
from .fsm import FSM
from .logic import calculate_and_create_charge
from django.conf import settings
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


async def _get_or_create_user(telegram_id):
    user, _ = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={'is_admin': telegram_id in settings.ADMIN_TELEGRAM_IDS}
    )
    return user


# =============== ОСНОВНЫЕ КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ ===============
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = await _get_or_create_user(update.effective_user.id)
#     msg = (
#         f"Привет! {'Вы — администратор.' if user.is_admin else 'Вы — участник.'}\n\n"
#         "Основные команды:\n"
#         "/submit_reading — ввести показания\n"
#         "/add_payment — внести оплату\n"
#         "/balance — узнать баланс"
#     )
#     if user.is_admin:
#         msg += (
#             "\n\nАдмин-команды:\n"
#             "/add_utility, /set_tariff\n"
#             "/list_users, /admin_submit_reading и др."
#         )
#     await update.message.reply_text(msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"✅ START received from Telegram ID: {update.effective_user.id}")
        user, created = User.objects.get_or_create(
            telegram_id=update.effective_user.id,
            defaults={'is_admin': update.effective_user.id in settings.ADMIN_TELEGRAM_IDS}
        )
        logger.info(f"✅ User {'created' if created else 'fetched'}: ID={user.telegram_id}, is_admin={user.is_admin}")

        msg = "Привет! Вы — администратор." if user.is_admin else "Привет! Вы — участник."
        await update.message.reply_text(msg)
        logger.info("✅ Reply sent successfully")

    except Exception as e:
        logger.exception("🔥 START handler FAILED with exception:")
        try:
            await update.message.reply_text("Ошибка при запуске.")
        except:
            pass


async def submit_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    utilities = Utility.objects.all()
    if not utilities.exists():
        await update.message.reply_text("Услуги не настроены. Обратитесь к администратору.")
        return
    buttons = [[InlineKeyboardButton(u.name, callback_data=f"util:{u.id}")] for u in utilities]
    await update.message.reply_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(buttons))
    FSM.set_state(user, "awaiting_utility_choice")


async def add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    await update.message.reply_text("Введите сумму оплаты (только число, например: 1500.50):")
    FSM.set_state(user, "awaiting_payment_amount")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    total_charges = sum(c.amount for c in user.charge_set.all())
    total_payments = sum(p.amount for p in user.payment_set.all())
    balance = total_payments - total_charges
    sign = "Переплата" if balance > 0 else "Долг" if balance < 0 else "Баланс нулевой"
    await update.message.reply_text(f"{sign}: {abs(balance):.2f} руб.")


# =============== АДМИН: УПРАВЛЕНИЕ УСЛУГАМИ И ТАРИФАМИ ===============

async def add_utility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Эта команда доступна только администратору.")
        return
    await update.message.reply_text("Введите название услуги (например: «Электричество»):")
    FSM.set_state(user, "admin_add_utility_name")


async def set_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Эта команда доступна только администратору.")
        return
    utilities = Utility.objects.all()
    if not utilities.exists():
        await update.message.reply_text("Нет услуг. Сначала добавьте через /add_utility.")
        return
    buttons = [[InlineKeyboardButton(u.name, callback_data=f"tariff_util:{u.id}")] for u in utilities]
    await update.message.reply_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(buttons))
    FSM.set_state(user, "admin_awaiting_utility_for_tariff")


async def delete_utility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    utilities = Utility.objects.all()
    if not utilities:
        await update.message.reply_text("Нет услуг для удаления.")
        return
    buttons = [[InlineKeyboardButton(u.name, callback_data=f"del_util:{u.id}")] for u in utilities]
    await update.message.reply_text(
        "Выберите услугу для удаления.\n⚠️ Удаление невозможно, если есть показания или начисления.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def delete_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    utilities = Utility.objects.filter(tariff__isnull=False).distinct()
    if not utilities:
        await update.message.reply_text("Нет тарифов для удаления.")
        return
    buttons = [[InlineKeyboardButton(u.name, callback_data=f"del_t_util:{u.id}")] for u in utilities]
    await update.message.reply_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(buttons))


async def list_utilities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    utilities = Utility.objects.all().order_by('name')
    if not utilities:
        await update.message.reply_text("Нет зарегистрированных услуг.")
        return
    text = "📋 Список услуг:\n\n"
    for u in utilities:
        text += f"• {u.name} (единица: {u.unit}, ID: {u.id})\n"
    await update.message.reply_text(text)


async def list_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    utilities = Utility.objects.all().order_by('name')
    if not utilities:
        await update.message.reply_text("Нет услуг → тарифы отсутствуют.")
        return
    text = "💰 Активные тарифы (последние):\n\n"
    any_tariff = False
    for utility in utilities:
        latest_tariff = Tariff.objects.filter(utility=utility).order_by('-valid_from').first()
        if latest_tariff:
            any_tariff = True
            from_date = latest_tariff.valid_from.strftime('%Y-%m-%d %H:%M')
            text += f"• {utility.name}: {latest_tariff.rate} руб./{utility.unit} (с {from_date})\n"
        else:
            text += f"• {utility.name}: тариф не задан\n"
    if not any_tariff:
        text = "Ни для одной услуги тариф не установлен."
    await update.message.reply_text(text)


# =============== АДМИН: ПРОСМОТР ДАННЫХ И ВВОД ОТ ИМЕНИ ===============

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    users = User.objects.prefetch_related('charge_set', 'payment_set').all()
    if not users:
        await update.message.reply_text("Нет зарегистрированных пользователей.")
        return
    text = "👥 Участники:\n\n"
    for u in users:
        total_charges = sum(c.amount for c in u.charge_set.all())
        total_payments = sum(p.amount for p in u.payment_set.all())
        balance = total_payments - total_charges
        status = "🟢" if balance >= 0 else "🔴"
        text += f"{status} ID: {u.telegram_id} | Баланс: {balance:+.2f} руб.\n"
    await update.message.reply_text(text)


async def user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    if not context.args:
        await update.message.reply_text("Укажите Telegram ID: /user_balance 123456789")
        return
    try:
        target_id = int(context.args[0])
        target_user = User.objects.get(telegram_id=target_id)
    except (ValueError, User.DoesNotExist):
        await update.message.reply_text("Пользователь не найден.")
        return
    charges = target_user.charge_set.select_related('utility').order_by('-period_end')
    payments = target_user.payment_set.order_by('-timestamp')
    text = f"📊 Баланс пользователя {target_id}:\n\n"
    text += "Начисления:\n"
    for c in charges[:5]:
        text += f"  • {c.utility.name}: {c.amount} руб. ({c.period_end.strftime('%Y-%m-%d')})\n"
    if not charges:
        text += "  — нет начислений\n"
    text += "\nОплаты:\n"
    for p in payments[:5]:
        text += f"  • {p.amount} руб. ({p.timestamp.strftime('%Y-%m-%d %H:%M')})\n"
    if not payments:
        text += "  — нет оплат\n"
    total_charges = sum(c.amount for c in charges)
    total_payments = sum(p.amount for p in payments)
    balance = total_payments - total_charges
    text += f"\nИтого: {balance:+.2f} руб."
    await update.message.reply_text(text)


async def admin_submit_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    users = User.objects.exclude(telegram_id=user.telegram_id)
    if not users:
        await update.message.reply_text("Нет других участников.")
        return
    buttons = [[InlineKeyboardButton(f"ID: {u.telegram_id}", callback_data=f"admin_read_user:{u.telegram_id}")] for u in users]
    await update.message.reply_text("Выберите пользователя:", reply_markup=InlineKeyboardMarkup(buttons))
    FSM.set_state(user, "admin_choosing_user_for_reading")


async def admin_add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    if not user.is_admin:
        await update.message.reply_text("Только для админа.")
        return
    users = User.objects.exclude(telegram_id=user.telegram_id)
    if not users:
        await update.message.reply_text("Нет других участников.")
        return
    buttons = [[InlineKeyboardButton(f"ID: {u.telegram_id}", callback_data=f"admin_pay_user:{u.telegram_id}")] for u in users]
    await update.message.reply_text("Выберите пользователя для оплаты:", reply_markup=InlineKeyboardMarkup(buttons))
    FSM.set_state(user, "admin_choosing_user_for_payment")


# =============== ОБРАБОТКА CALLBACK-ЗАПРОСОВ ===============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await _get_or_create_user(update.effective_user.id)

    # Удаление услуги
    if query.data.startswith("del_util:"):
        if not user.is_admin:
            await query.edit_message_text("Недоступно.")
            return
        utility_id = int(query.data.split(":")[1])
        try:
            utility = Utility.objects.get(id=utility_id)
            if MeterReading.objects.filter(utility=utility).exists() or Charge.objects.filter(utility=utility).exists():
                await query.edit_message_text(f"❌ Невозможно удалить «{utility.name}»: есть привязанные данные.")
            else:
                utility.delete()
                await query.edit_message_text(f"✅ Услуга «{utility.name}» удалена.")
        except Utility.DoesNotExist:
            await query.edit_message_text("Услуга не найдена.")
        return

    # Удаление тарифа: выбор услуги
    if query.data.startswith("del_t_util:"):
        if not user.is_admin:
            await query.edit_message_text("Недоступно.")
            return
        utility_id = int(query.data.split(":")[1])
        try:
            utility = Utility.objects.get(id=utility_id)
            tariffs = Tariff.objects.filter(utility=utility).order_by('-valid_from')
            if not tariffs:
                await query.edit_message_text(f"У услуги «{utility.name}» нет тарифов.")
                return
            buttons = []
            for t in tariffs:
                label = f"{t.rate} руб. (с {t.valid_from.strftime('%Y-%m-%d')})"
                buttons.append([InlineKeyboardButton(label, callback_data=f"del_t:{t.id}")])
            buttons.append([InlineKeyboardButton("← Назад", callback_data="back_to_del_tariff_util")])
            await query.edit_message_text(
                f"Выберите тариф для удаления из «{utility.name}»:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            FSM.set_state(user, "admin_deleting_tariff", {"utility_id": utility_id})
        except Utility.DoesNotExist:
            await query.edit_message_text("Услуга не найдена.")
        return

    # Удаление тарифа: выбор конкретного
    if query.data.startswith("del_t:"):
        if not user.is_admin:
            await query.edit_message_text("Недоступно.")
            return
        tariff_id = int(query.data.split(":")[1])
        try:
            tariff = Tariff.objects.select_related('utility').get(id=tariff_id)
            utility = tariff.utility
            remaining_count = Tariff.objects.filter(utility=utility).count()
            warning = "\n\n⚠️ Это последний тариф для услуги!" if remaining_count == 1 else ""
            tariff.delete()
            await query.edit_message_text(
                f"✅ Тариф {tariff.rate} руб./{utility.unit} (с {tariff.valid_from.strftime('%Y-%m-%d')}) удалён.{warning}"
            )
        except Tariff.DoesNotExist:
            await query.edit_message_text("Тариф не найден.")
        return

    # Назад к выбору услуги при удалении тарифа
    if query.data == "back_to_del_tariff_util":
        if not user.is_admin:
            await query.edit_message_text("Недоступно.")
            return
        utilities = Utility.objects.filter(tariff__isnull=False).distinct()
        if not utilities:
            await query.edit_message_text("Нет тарифов для удаления.")
            return
        buttons = [[InlineKeyboardButton(u.name, callback_data=f"del_t_util:{u.id}")] for u in utilities]
        await query.edit_message_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(buttons))
        FSM.clear_state(user)
        return

    # Выбор услуги для тарифа (установка)
    if query.data.startswith("tariff_util:"):
        if not user.is_admin:
            await query.edit_message_text("Недоступно.")
            return
        utility_id = int(query.data.split(":")[1])
        FSM.set_state(user, "admin_awaiting_tariff_value", {"utility_id": utility_id})
        await query.edit_message_text("Введите тариф (руб. за единицу, например: 6.50):")
        return

    # Выбор пользователя для ввода показаний
    if query.data.startswith("admin_read_user:"):
        if not user.is_admin:
            return
        target_id = int(query.data.split(":")[1])
        utilities = Utility.objects.all()
        if not utilities:
            await query.edit_message_text("Нет услуг.")
            return
        buttons = [[InlineKeyboardButton(u.name, callback_data=f"admin_read_util:{target_id}:{u.id}")] for u in utilities]
        await query.edit_message_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # Выбор услуги для показаний (админ от имени)
    if query.data.startswith("admin_read_util:"):
        if not user.is_admin:
            return
        _, target_id, util_id = query.data.split(":")
        target_id, util_id = int(target_id), int(util_id)
        FSM.set_state(user, "admin_awaiting_reading_value", {"target_user_id": target_id, "utility_id": util_id})
        await query.edit_message_text("Введите показания (число):")
        return

    # Выбор пользователя для оплаты (админ от имени)
    if query.data.startswith("admin_pay_user:"):
        if not user.is_admin:
            return
        target_id = int(query.data.split(":")[1])
        FSM.set_state(user, "admin_awaiting_payment_value", {"target_user_id": target_id})
        await query.edit_message_text("Введите сумму оплаты (число):")
        return

    # Выбор услуги для показаний (обычный пользователь)
    if query.data.startswith("util:"):
        utility_id = int(query.data.split(":")[1])
        FSM.set_state(user, "awaiting_reading_value", {"utility_id": utility_id})
        await query.edit_message_text("Введите показания (только число):")
        return


# =============== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ (FSM) ===============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update.effective_user.id)
    state, ctx = FSM.get_state(user)

    # === АДМИН: добавление услуги ===
    if state == "admin_add_utility_name":
        name = update.message.text.strip()
        if not name:
            await update.message.reply_text("Название не может быть пустым. Попробуйте снова:")
            return
        if Utility.objects.filter(name=name).exists():
            await update.message.reply_text(f"Услуга «{name}» уже существует.")
        else:
            utility = Utility.objects.create(name=name, unit="ед.")
            await update.message.reply_text(f"Услуга «{utility.name}» добавлена.")
        FSM.clear_state(user)
        return

    # === АДМИН: ввод тарифа ===
    if state == "admin_awaiting_tariff_value":
        try:
            rate = Decimal(update.message.text.replace(',', '.'))
            if rate <= 0:
                raise ValueError()
            utility_id = ctx.get("utility_id")
            utility = Utility.objects.get(id=utility_id)
            Tariff.objects.create(utility=utility, rate=rate, valid_from=update.message.date)
            await update.message.reply_text(f"Тариф для «{utility.name}» установлен: {rate} руб./{utility.unit}")
            FSM.clear_state(user)
            return
        except (InvalidOperation, ValueError, Utility.DoesNotExist):
            await update.message.reply_text("Некорректное значение. Введите положительное число (например: 7.50):")
            return

    # === АДМИН: ввод показаний от имени ===
    if state == "admin_awaiting_reading_value":
        if not user.is_admin:
            FSM.clear_state(user)
            return
        try:
            value = Decimal(update.message.text.replace(',', '.'))
            if value < 0:
                raise ValueError()
            target_user = User.objects.get(telegram_id=ctx["target_user_id"])
            utility = Utility.objects.get(id=ctx["utility_id"])
            success = calculate_and_create_charge(target_user, utility, value, update.message.date)
            if success:
                msg = f"✅ Показания за {target_user.telegram_id} приняты. Начисление создано."
            else:
                msg = f"✅ Показания за {target_user.telegram_id} сохранены."
            await update.message.reply_text(msg)
            FSM.clear_state(user)
        except Exception as e:
            logger.exception("Ошибка при вводе показаний админом")
            await update.message.reply_text("Ошибка. Убедитесь, что услуга и пользователь существуют.")
            FSM.clear_state(user)
        return

    # === АДМИН: ввод оплаты от имени ===
    if state == "admin_awaiting_payment_value":
        if not user.is_admin:
            FSM.clear_state(user)
            return
        try:
            amount = Decimal(update.message.text.replace(',', '.'))
            if amount <= 0:
                raise ValueError()
            target_user = User.objects.get(telegram_id=ctx["target_user_id"])
            Payment.objects.create(user=target_user, amount=amount, timestamp=update.message.date)
            await update.message.reply_text(f"✅ Оплата {amount} руб. учтена за пользователя {target_user.telegram_id}.")
            FSM.clear_state(user)
        except Exception as e:
            await update.message.reply_text("Ошибка. Сумма должна быть > 0.")
            FSM.clear_state(user)
        return

    # === ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ: ввод показаний ===
    if state == "awaiting_reading_value":
        try:
            value = Decimal(update.message.text.replace(',', '.'))
            if value < 0:
                raise ValueError()
            utility = Utility.objects.get(id=ctx["utility_id"])
            success = calculate_and_create_charge(user, utility, value, update.message.date)
            if success:
                await update.message.reply_text(f"Начисление создано.")
            else:
                await update.message.reply_text("Показания приняты, но начисление не требуется.")
            FSM.clear_state(user)
        except Exception as e:
            await update.message.reply_text("Некорректное значение. Попробуйте снова (только число ≥ 0):")
        return

    # === ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ: ввод оплаты ===
    if state == "awaiting_payment_amount":
        try:
            amount = Decimal(update.message.text.replace(',', '.'))
            if amount <= 0:
                raise ValueError()
            Payment.objects.create(user=user, amount=amount, timestamp=update.message.date)
            await update.message.reply_text(f"Оплата на {amount} руб. учтена.")
            FSM.clear_state(user)
        except (InvalidOperation, ValueError):
            await update.message.reply_text("Введите корректную сумму (> 0):")
        return

    # === НЕИЗВЕСТНОЕ СОСТОЯНИЕ ===
    base_msg = (
        "Используйте команды:\n"
        "/submit_reading — ввести показания\n"
        "/add_payment — внести оплату\n"
        "/balance — узнать баланс"
    )
    if user.is_admin:
        base_msg += "\n\nДля админа: /add_utility, /list_users и др."
    await update.message.reply_text(base_msg)