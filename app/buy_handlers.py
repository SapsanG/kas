# app/buy_handlers.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context, db_session
from config.logging_config import logger

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Команда /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_context = get_user_context(user_id)
    
    if len(context.args) != 2:
        await update.message.reply_text('Использование: /buy <symbol> <amount>')
        return
    
    symbol = context.args[0].upper()
    amount = float(context.args[1])
    
    try:
        mexc_instance = user_context.get_mexc_instance()
        order = mexc_instance.create_market_buy_order(symbol, amount)
        logger.info(f"Выполнена покупка для пользователя {user_id}: {order}")
        await update.message.reply_text(f'Заказ выполнен успешно: {order}')
    except Exception as e:
        logger.error(f"Ошибка при покупке для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Ошибка при покупке: {e}")