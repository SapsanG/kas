# app/settings_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context  # Импортируем get_user_context
from config.logging_config import logger
from utils.validation import ValidationError, validate_positive_number, validate_api_key, validate_api_secret

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Команда /set_params
async def set_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /set_params вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if len(context.args) != 4:
        await update.message.reply_text('Использование: /set_params <процент_прибыли> <процент_падения> <задержка> <размер_ордера>')
        return
    
    try:
        profit_percentage = float(context.args[0])
        fall_percentage = float(context.args[1])
        delay_seconds = int(context.args[2])
        order_size = float(context.args[3])
        
        # Валидация параметров
        validate_positive_number(profit_percentage, "Процент прибыли")
        validate_positive_number(fall_percentage, "Процент падения")
        validate_positive_number(delay_seconds, "Задержка")
        validate_positive_number(order_size, "Размер ордера")
        
        old_params = {
            "profit_percentage": user_context.bot_params.profit_percentage,
            "fall_percentage": user_context.bot_params.fall_percentage,
            "delay_seconds": user_context.bot_params.delay_seconds,
            "order_size": user_context.bot_params.order_size,
        }
        
        # Устанавливаем новые параметры
        user_context.bot_params.set_params(profit_percentage, fall_percentage, delay_seconds, order_size)
        user_context.save_user_params()  # Сохраняем изменения в базе данных
        
        if (
            old_params["profit_percentage"] == user_context.bot_params.profit_percentage and
            old_params["fall_percentage"] == user_context.bot_params.fall_percentage and
            old_params["delay_seconds"] == user_context.bot_params.delay_seconds and
            old_params["order_size"] == user_context.bot_params.order_size
        ):
            await update.message.reply_text(
                f'Параметры не изменились.\n'
                f'Текущие параметры:\n'
                f'Процент прибыли: {user_context.bot_params.profit_percentage}%\n'
                f'Процент падения: {user_context.bot_params.fall_percentage}%\n'
                f'Задержка: {user_context.bot_params.delay_seconds} секунд\n'
                f'Размер ордера: ${user_context.bot_params.order_size}'
            )
        else:
            await update.message.reply_text(
                f'Параметры успешно обновлены:\n'
                f'Процент прибыли: {user_context.bot_params.profit_percentage}%\n'
                f'Процент падения: {user_context.bot_params.fall_percentage}%\n'
                f'Задержка: {user_context.bot_params.delay_seconds} секунд\n'
                f'Размер ордера: ${user_context.bot_params.order_size}'
            )
    
    except ValidationError as e:
        logger.error(f"Ошибка валидации параметров для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}')
    except ValueError as e:
        logger.error(f"Ошибка преобразования параметров для пользователя {user_id}: {e}")
        await update.message.reply_text('Ошибка: все параметры должны быть числами.')

# Команда /set_api_keys
async def set_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /set_api_keys вызвана пользователем {user_id}")
    
    if len(context.args) != 2:
        await update.message.reply_text('Использование: /set_api_keys <api_key> <api_secret>')
        return
    
    api_key = context.args[0]
    api_secret = context.args[1]
    
    try:
        # Получаем контекст пользователя
        user_context = get_user_context(user_id)
        
        # Устанавливаем API-ключи
        user_context.set_api_credentials(api_key, api_secret)
        user_context.save_user_params()  # Сохраняем изменения в базе данных
        
        await update.message.reply_text('API-ключи успешно установлены.')
    
    except ValidationError as e:
        logger.error(f"Ошибка валидации API-ключей для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}')
    except Exception as e:
        logger.error(f"Ошибка при установке API-ключей для пользователя {user_id}: {e}")
        await update.message.reply_text('Ошибка при установке API-ключей.')

# Команда /check_api_keys
async def check_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /check_api_keys вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if user_context.api_key and user_context.api_secret:
        await update.message.reply_text(f'Ваши API-ключи:\nAPI Key: {user_context.api_key}\nAPI Secret: {user_context.api_secret}')
    else:
        await update.message.reply_text('API-ключи не установлены.')

# Команда /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /stats вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    reply = (
        f"Статистика торговли для пользователя {user_id}:\n"
        f"Текущий уровень: {user_context.current_level}\n"
        f"Выполненные покупки: {list(user_context.buy_executed.keys())}\n"
        f"Текущая цена покупки: ${user_context.bot_params.buy_price or 'Не определена'}\n"
    )
    await update.message.reply_text(reply)