# app/trading_logic.py

import asyncio
import logging
from ..config.config import API_KEY, API_SECRET  # Импортируем конфигурацию
from .shared import bot_state_manager, get_user_context  # Импортируем необходимые компоненты
from telegram import Update

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_trading(symbol: str, update: Update) -> None:
    user_id = update.effective_user.id
    logger.info(f"Автоматическая торговля запущена для пользователя {user_id}.")

    # Получаем контекст пользователя
    user_context = get_user_context(user_id)

    if bot_state_manager.is_trading_active(user_id):
        await update.message.reply_text('Автоматическая торговля уже запущена. Чтобы остановить, используйте команду /stop.')
        return

    bot_state_manager.start(user_id)  # Отмечаем, что торговля запущена для этого пользователя
    await update.message.reply_text(f'Автоматическая торговля запущена для {symbol}. Чтобы остановить, используйте команду /stop.')

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
                logger.info(f"Выполнена покупка для пользователя {user_id}: {buy_order}")
                await update.message.reply_text(f'Выполнена покупка: {buy_order}')

                # Обновляем цену покупки в контексте пользователя
                user_context.bot_params.buy_price = ticker['ask']  # Новая цена покупки

                # Выставляем ордер на продажу
                sell_order = mexc_instance.create_limit_sell_order(symbol, buy_order['amount'], sell_price)
                logger.info(f"Выставлен ордер на продажу для пользователя {user_id}: {sell_order}")
                await update.message.reply_text(f'Выставлен ордер на продажу: {sell_order}')

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