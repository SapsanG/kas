# app/main.py
import os
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

# Абсолютные импорты
from config.config import TOKEN, DATABASE_URL, ADMIN_ID
from app.database import db_session
from config.logging_config import logger

# Глобальная переменная application
application = None

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Скрыть INFO-сообщения httpx

# Главная функция
def main() -> None:
    global application  # Используем глобальную переменную
    try:
        logger.info("Бот успешно запущен!")
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        from app.handlers import start
        from app.buy_handlers import buy  # Убедись, что здесь есть buy
        from app.profit_handlers import profit_today, profit_history, profit_month, profit_total
        from app.settings_handlers import set_params, set_api_keys, check_api_keys, stats
        from app.autotrade_handlers import autobuy, stop

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("buy", buy))  # Добавляем buy
        application.add_handler(CommandHandler("set_params", set_params))
        application.add_handler(CommandHandler("autobuy", autobuy))
        application.add_handler(CommandHandler("stop", stop))
        application.add_handler(CommandHandler("set_api_keys", set_api_keys))
        application.add_handler(CommandHandler("check_api_keys", check_api_keys))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("profit_today", profit_today))
        application.add_handler(CommandHandler("profit_history", profit_history))
        application.add_handler(CommandHandler("profit_month", profit_month))
        application.add_handler(CommandHandler("profit_total", profit_total))
        
        application.run_polling()
    except Exception as e:
        error_message = f"Критическая ошибка при запуске бота: {e}"
        logger.error(error_message)
        asyncio.run(send_error_notification(error_message))

# Функция для отправки уведомлений администратору
async def send_error_notification(error_message: str):
    global application  # Используем глобальную переменную
    if application:
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text=f"Ошибка в боте:\n{error_message}")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору: {e}")

# Точка входа в программу
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        error_message = f"Неизвестная ошибка: {e}"
        logger.error(error_message)
        asyncio.run(send_error_notification(error_message))
    finally:
        db_session.close()  # Закрываем сессию
        logger.info("Завершение работы бота...")