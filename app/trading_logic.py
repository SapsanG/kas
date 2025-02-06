# app/trading_logic.py
import asyncio
import logging
from ..config.config import API_KEY, API_SECRET  # Импортируем конфигурацию
from .shared import mexc, bot_params, is_running  # Импортируем общие ресурсы
from telegram import Update

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_trading(symbol: str, update: Update) -> None:
    global is_running
    is_running = True
    await update.message.reply_text(f'Автоматическая торговля запущена для {symbol}. Чтобы остановить, используйте команду /stop.')
    
    while is_running:
        try:
            ticker = mexc.fetch_ticker(symbol)
            current_bid_price = ticker['bid']  # Текущая цена покупки
            
            if not bot_params.buy_price:
                bot_params.buy_price = current_bid_price  # Инициализация цены покупки
            
            sell_price = bot_params.buy_price * (1 + bot_params.profit_percentage / 100)
            fall_price = bot_params.buy_price * (1 - bot_params.fall_percentage / 100)
            
            balance = mexc.fetch_balance()
            usdt_balance = balance['USDT']['free']
            if usdt_balance < bot_params.order_size:
                logger.warning("Недостаточно средств для покупки.")
                await update.message.reply_text('Недостаточно средств для покупки.')
                break
            
            if current_bid_price <= fall_price:
                buy_amount = bot_params.order_size / ticker['ask']  # Используем ASK для покупки
                buy_order = mexc.create_market_buy_order(symbol, buy_amount)
                logger.info(f"Выполнена покупка: {buy_order}")
                await update.message.reply_text(f'Выполнена покупка: {buy_order}')
                
                # Обновляем цену покупки
                bot_params.buy_price = ticker['ask']  # Новая цена покупки
                
                # Выставляем ордер на продажу
                sell_order = mexc.create_limit_sell_order(symbol, buy_order['amount'], sell_price)
                logger.info(f"Выставлен ордер на продажу: {sell_order}")
                await update.message.reply_text(f'Выставлен ордер на продажу: {sell_order}')
            
            await asyncio.sleep(bot_params.delay_seconds)
        
        except Exception as e:
            logger.error(f"Ошибка при автоматической торговле: {e}")
            await update.message.reply_text(f'Ошибка при автоматической торговле: {e}')
            break
    
    is_running = False
    logger.info("Автоматическая торговля остановлена.")
    await update.message.reply_text('Автоматическая торговля остановлена.')