# trading_logic.py

import asyncio
import logging
from app.shared import bot_state_manager, get_user_context  # Импортируем необходимые компоненты
from telegram import Update
import ccxt  # Импортируем ccxt

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

    first_trade = True  # Флаг для первой сделки

    while bot_state_manager.is_trading_active(user_id):  # Проверяем состояние торговли для конкретного пользователя
        try:
            mexc_instance = user_context.get_mexc_instance()  # Получаем экземпляр MEXC для пользователя
            ticker = await mexc_instance.fetch_ticker(symbol)
            current_bid_price = ticker['bid']  # Текущая цена покупки
            current_ask_price = ticker['ask']  # Текущая цена продажи

            # Логирование текущих значений
            logger.info(f"Текущие данные для пользователя {user_id}: "
                        f"buy_price={user_context.bot_params.buy_price}, "
                        f"current_bid_price={current_bid_price}, "
                        f"current_ask_price={current_ask_price}")

            buy_price = user_context.bot_params.buy_price or current_bid_price
            if not user_context.bot_params.buy_price:
                user_context.bot_params.buy_price = current_bid_price

            sell_price = buy_price * (1 + user_context.bot_params.profit_percentage / 100)
            fall_price = buy_price * (1 - user_context.bot_params.fall_percentage / 100)

            # Логирование расчётных значений
            logger.info(f"Расчётные данные для пользователя {user_id}: "
                        f"sell_price={sell_price:.6f}, fall_price={fall_price:.6f}")

            balance = await mexc_instance.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)  # Безопасно получаем доступный баланс USDT

            # Проверяем баланс и логируем информацию
            if usdt_balance < user_context.bot_params.order_size:
                logger.warning(f"Недостаточно средств для покупки у пользователя {user_id}. "
                               f"Текущий баланс USDT: {usdt_balance}, требуется: {user_context.bot_params.order_size}")
                await update.message.reply_text(f'Недостаточно средств для покупки. '
                                                f'Текущий баланс USDT: {usdt_balance:.2f}, '
                                                f'требуется: {user_context.bot_params.order_size:.2f}')
                break

            # Выполняем первую сделку без условия падения
            if first_trade:
                cost = user_context.bot_params.order_size  # Сумма в долларах для покупки

                # Логирование параметров первой покупки
                logger.info(f"Выполнение первой покупки для пользователя {user_id}: "
                            f"symbol={symbol}, cost={cost}, current_ask_price={current_ask_price}")

                # Проверяем минимальные требования биржи
                market = mexc_instance.market(symbol)
                min_cost = float(market['limits']['cost']['min']) if market['limits']['cost']['min'] else 0
                min_amount = float(market['limits']['amount']['min']) if market['limits']['amount']['min'] else 0

                # Логирование минимальных требований
                logger.info(f"Минимальные требования для символа {symbol}: "
                            f"min_cost={min_cost}, min_amount={min_amount}")

                if cost < min_cost:
                    logger.error(f"Ошибка: сумма ордера ({cost}) меньше минимальной суммы ({min_cost}) для символа {symbol}.")
                    await update.message.reply_text(f'Ошибка: сумма ордера меньше минимальной суммы для символа {symbol}.')
                    break

                # Выполняем рыночную покупку на основе стоимости
                try:
                    buy_order = await mexc_instance.create_market_buy_order(symbol, cost)
                    logger.info(f"Первая покупка выполнена для пользователя {user_id}: {buy_order}")
                    await update.message.reply_text(
                        f'Выполнена первая покупка:\n'
                        f'Символ: {symbol}\n'
                        f'Количество: {buy_order["amount"]:.6f}\n'
                        f'Цена: ${ticker["ask"]:.6f}\n'
                        f'Общая стоимость: ${cost:.2f}'
                    )

                    # Обновляем цену покупки в контексте пользователя
                    user_context.bot_params.buy_price = ticker['ask']
                    user_context.current_level += 1  # Увеличиваем текущий уровень

                    # Выставляем ордер на продажу
                    sell_order = await mexc_instance.create_limit_sell_order(symbol, buy_order['amount'], sell_price)
                    logger.info(f"Первый ордер на продажу создан для пользователя {user_id}: {sell_order}")
                    await update.message.reply_text(
                        f'Выполнен первый ордер на продажу:\n'
                        f'Символ: {symbol}\n'
                        f'Количество: {buy_order["amount"]:.6f}\n'
                        f'Цена: ${sell_price:.6f}'
                    )

                    first_trade = False  # Сбрасываем флаг первой сделки

                except ccxt.InvalidOrder as e:
                    logger.error(f"Ошибка создания первого ордера для пользователя {user_id}: {e}")
                    await update.message.reply_text(f'Ошибка создания первого ордера: {e}')
                    break
                except Exception as e:
                    logger.error(f"Неизвестная ошибка при первой покупке для пользователя {user_id}: {e}")
                    await update.message.reply_text(f'Произошла ошибка при первой покупке: {e}')
                    break

        except ccxt.NetworkError as e:
            logger.error(f"Ошибка сети при выполнении ордера для пользователя {user_id}: {e}")
            await update.message.reply_text(f'Ошибка сети: {e}')
            break
        except Exception as e:
            logger.error(f"Неизвестная ошибка при торговле для пользователя {user_id}: {e}")
            await update.message.reply_text(f'Произошла ошибка: {e}')
            break

    bot_state_manager.stop(user_id)
    logger.info(f"Торговля остановлена для пользователя {user_id}.")