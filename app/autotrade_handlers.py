# app/autotrade_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import bot_state_manager, get_user_context  # Импортируем необходимые компоненты
from config.logging_config import logger
from .contexts import UserContext  # Добавляем импорт UserContext
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Глобальная переменная is_running
is_running = {}

# Команда /autobuy
async def autobuy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /autobuy вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if bot_state_manager.is_trading_active(user_id):
        await update.message.reply_text('Автоматическая торговля уже запущена. Чтобы остановить, используйте команду /stop.')
        return
    
    symbol = "KAS/USDT"
    bot_state_manager.start(user_id)  # Отмечаем, что торговля запущена для этого пользователя
    asyncio.create_task(start_trading(symbol, update, user_context, user_id))
    await update.message.reply_text(f'Автоматическая торговля запущена для {symbol}. Чтобы остановить, используйте команду /stop.')

# Команда /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /stop вызвана пользователем {user_id}")
    
    if not bot_state_manager.is_trading_active(user_id):
        await update.message.reply_text('Автоматическая торговля не запущена.')
        return
    
    bot_state_manager.stop(user_id)
    await update.message.reply_text('Автоматическая торговля остановлена.')

# Функция для автоматической торговли
async def start_trading(symbol: str, update: Update, user_context: 'UserContext', user_id: int):
    global is_running
    
    while bot_state_manager.is_trading_active(user_id):  # Проверяем состояние торговли для конкретного пользователя
        try:
            mexc_instance = user_context.get_mexc_instance()  # Получаем экземпляр MEXC для пользователя
            
            ticker = mexc_instance.fetch_ticker(symbol)
            current_bid_price = ticker['bid']
            
            buy_price = user_context.bot_params.buy_price or current_bid_price
            if not user_context.bot_params.buy_price:
                user_context.bot_params.buy_price = current_bid_price
            
            # Определяем текущий уровень сетки
            fall_percentage = user_context.bot_params.fall_percentage
            level = int((buy_price - current_bid_price) / (buy_price * (fall_percentage / 100))) + 1
            
            current_level = user_context.current_level
            if level > current_level:
                user_context.current_level = level
                
                if level not in user_context.buy_executed or not user_context.buy_executed.get(level, False):
                    buy_order_amount = user_context.bot_params.order_size / ticker['ask']
                    buy_order = mexc_instance.create_market_buy_order(symbol, buy_order_amount)
                    
                    # Логируем покупку
                    user_context.log_trade("buy", symbol, buy_order['amount'], ticker['ask'], profit=0)
                    
                    logger.info(f"Выполнена покупка Buy({level}) для пользователя {user_id}: {buy_order}")
                    await update.message.reply_text(f'Выполнена покупка Buy({level}): {buy_order}')
                    
                    # Обновляем цену покупки
                    user_context.bot_params.buy_price = ticker['ask']
                    
                    # Создаем ордер на продажу
                    sell_price = user_context.bot_params.buy_price * (1 + user_context.bot_params.profit_percentage / 100)
                    sell_order = mexc_instance.create_limit_sell_order(symbol, buy_order['amount'], sell_price)
                    logger.info(f"Создан ордер на продажу Sell({level}) для пользователя {user_id}: {sell_order}")
                    await update.message.reply_text(f'Создан ордер на продажу Sell({level}): {sell_order}')
            
            # Проверяем уровни для продажи
            for executed_level in list(user_context.buy_executed.keys()):
                sell_price = user_context.bot_params.buy_price * (1 + user_context.bot_params.profit_percentage / 100)
                if current_bid_price >= sell_price:
                    sell_order = mexc_instance.create_market_sell_order(symbol, buy_order['amount'])
                    
                    # Рассчитываем прибыль
                    profit = (current_bid_price - user_context.bot_params.buy_price) * sell_order['amount']
                    
                    # Логируем продажу
                    user_context.log_trade("sell", symbol, sell_order['amount'], current_bid_price, profit=profit)
                    
                    logger.info(f"Выполнена продажа Sell({executed_level}) для пользователя {user_id}: {sell_order}, Прибыль: ${profit:.2f}")
                    await update.message.reply_text(f'Выполнена продажа Sell({executed_level}): {sell_order}, Прибыль: ${profit:.2f}')
            
            # Добавляем задержку между операциями
            await asyncio.sleep(user_context.bot_params.delay_seconds)
        
        except Exception as e:
            logger.error(f"Ошибка при автоматической торговле для пользователя {user_id}: {e}")
            await update.message.reply_text(f'Ошибка при автоматической торговле: {e}')
            break
    
    # Останавливаем торговлю для пользователя
    bot_state_manager.stop(user_id)
    logger.info(f"Автоматическая торговля остановлена для пользователя {user_id}.")
    await update.message.reply_text('Автоматическая торговля остановлена.')