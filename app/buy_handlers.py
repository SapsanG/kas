# app/buy_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.contexts import UserContext  # Импортируем UserContext
from app.shared import db_session  # Предполагается, что здесь есть логика работы с базой данных
from config.logging_config import logger
import ccxt  # Импортируем ccxt

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Вспомогательная функция для получения контекста пользователя
def get_user_context(user_id: int) -> UserContext:
    """
    Создает или возвращает существующий контекст пользователя.

    :param user_id: Уникальный идентификатор пользователя.
    :return: Экземпляр UserContext.
    """
    # Здесь можно добавить логику загрузки контекста пользователя из базы данных
    # Если контекст не найден, создаем новый
    user_context = db_session.query(UserContext).filter_by(user_id=user_id).first()
    if not user_context:
        user_context = UserContext(user_id=user_id)
        db_session.add(user_context)
        db_session.commit()  # Сохраняем новый контекст в базе данных
    return user_context

# Команда /balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /balance вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    try:
        # Получаем экземпляр Mexc из контекста пользователя
        mexc_instance = user_context.get_data("mexc_instance")
        if not mexc_instance:
            raise ValueError("API-ключи не установлены. Используйте /set_api_keys.")
        
        # Получаем баланс
        balances = mexc_instance.fetch_balance()
        logger.info(f"Полный ответ fetch_balance() для пользователя {user_id}: {balances}")
        
        reply = "Ваш баланс:\n"
        for currency, balance_info in balances.items():
            if isinstance(balance_info, dict) and 'total' in balance_info and balance_info['total'] is not None and balance_info['total'] > 0:
                reply += f"{currency}: {balance_info['total']:.4f}\n"
        
        if not reply.strip():  # Если баланс пустой
            reply = "Ваш баланс пуст."
        
        await update.message.reply_text(reply)
    
    except ccxt.AuthenticationError as e:
        logger.error(f"Ошибка аутентификации для пользователя {user_id}: {e}")
        await update.message.reply_text("Ошибка аутентификации. Проверьте свои API-ключи.")
    except ccxt.NetworkError as e:
        logger.error(f"Ошибка сети при получении баланса для пользователя {user_id}: {e}")
        await update.message.reply_text("Не удалось получить баланс из-за сетевой ошибки. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при получении баланса для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Команда /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /buy вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if len(context.args) != 2:
        await update.message.reply_text('Использование: /buy <symbol> <amount>')
        return
    
    symbol = context.args[0].upper()
    amount = float(context.args[1])
    
    try:
        # Получаем экземпляр Mexc из контекста пользователя
        mexc_instance = user_context.get_data("mexc_instance")
        if not mexc_instance:
            raise ValueError("API-ключи не установлены. Используйте /set_api_keys.")
        
        # Выполняем покупку
        order = mexc_instance.create_market_buy_order(symbol, amount)
        logger.info(f"Выполнена покупка для пользователя {user_id}: {order}")
        await update.message.reply_text(f'Заказ выполнен успешно: {order}')
    
    except ccxt.InsufficientFunds as e:
        logger.error(f"Недостаточно средств для покупки для пользователя {user_id}: {e}")
        await update.message.reply_text("Недостаточно средств для выполнения покупки.")
    except ccxt.AuthenticationError as e:
        logger.error(f"Ошибка аутентификации для пользователя {user_id}: {e}")
        await update.message.reply_text("Ошибка аутентификации. Проверьте свои API-ключи.")
    except ccxt.NetworkError as e:
        logger.error(f"Ошибка сети при покупке для пользователя {user_id}: {e}")
        await update.message.reply_text("Не удалось выполнить покупку из-за сетевой ошибки. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при покупке для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")