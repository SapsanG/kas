# app/autotrade_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import bot_state_manager, get_user_context  # Импортируем необходимые компоненты
from app.contexts import UserContext  # Добавляем импорт UserContext
from config.logging_config import logger
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Глобальная переменная для отслеживания состояния торговли
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
    while bot_state_manager.is_trading_active(user_id):  # Проверяем состояние торговли для конкретного пользователя
        try:
            mexc_instance = user_context.get_mexc_instance()  # Получаем экземпляр MEXC для пользователя
            
            ticker = mexc_instance.fetch_ticker(symbol)
            current_bid_price = ticker['bid']  # Текущая цена покупки

            buy_price = user_context.bot_params.buy_price or current_bid_price
            if not user_context.bot_params.buy_price:
                user_context.bot_params.buy_price = current_bid_price

            sell_price = buy_price * (1 + user_context.bot_params.profit_percentage / 100)
            fall_price = buy_price * (1 - user_context.bot_params.fall_percentage / 100)

            balance = mexc_instance.fetch_balance()
            usdt_balance = balance['USDT']['free']
            if usdt_balance < user_context.bot_params.order_size:
                logger.warning(f"Недостаточно средств для покупки у пользователя {user_id}.")
                await update.message.reply_text('Недостаточно средств для покупки.')
                break

            if current_bid_price <= fall_price:
                buy_amount = user_context.bot_params.order_size / ticker['ask']  # Используем ASK для покупки
                buy_order = mexc_instance.create_market_buy_order(symbol, buy_amount)
                
                # Логируем покупку
                user_context.log_trade("buy", symbol, buy_order['amount'], ticker['ask'], profit=0)
                
                logger.info(f"Выполнена покупка Buy({user_context.current_level}) для пользователя {user_id}: {buy_order}")
                await update.message.reply_text(f'Выполнена покупка: {buy_order}')

                # Обновляем цену покупки в контексте пользователя
                user_context.bot_params.buy_price = ticker['ask']
                user_context.current_level += 1  # Увеличиваем текущий уровень

                # Создаем ордер на продажу
                sell_order = mexc_instance.create_limit_sell_order(symbol, buy_order['amount'], sell_price)
                logger.info(f"Создан ордер на продажу Sell({user_context.current_level}) для пользователя {user_id}: {sell_order}")
                await update.message.reply_text(f'Создан ордер на продажу: {sell_order}')
            
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