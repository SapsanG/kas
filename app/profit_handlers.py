# app/profit_handlers.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context, db_session  # Импортируем необходимые ресурсы
from config.logging_config import logger

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Команда /profit_today
async def profit_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_context = get_user_context(user_id)
    profit = user_context.calculate_profit_today()
    await update.message.reply_text(f'Ваш профит за сегодня: ${profit:.2f}')

# Команда /profit_history
async def profit_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_context = get_user_context(user_id)

    if len(context.args) != 1:
        await update.message.reply_text('Использование: /profit_history <дни>')
        return

    try:
        days = int(context.args[0])
        if days <= 0:
            raise ValueError("Количество дней должно быть положительным числом.")
        profit = user_context.calculate_profit_period(days)
        await update.message.reply_text(f'Ваш профит за последние {days} дней: ${profit:.2f}')
    except ValueError as e:
        logger.error(f"Ошибка валидации периода для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}')

# Команда /profit_month
async def profit_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_context = get_user_context(user_id)
    profit = user_context.calculate_profit_month()
    await update.message.reply_text(f'Ваш профит за последний месяц: ${profit:.2f}')

# Команда /profit_total
async def profit_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_context = get_user_context(user_id)
    profit = user_context.calculate_profit_total()
    await update.message.reply_text(f'Ваш общий профит: ${profit:.2f}')