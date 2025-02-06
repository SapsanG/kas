# config/logging_config.py
import logging
from logging.handlers import RotatingFileHandler

# Настройка формата логов
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Создание логгера
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Обработчик для вывода логов в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # Выводить только WARNING и выше
console_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(console_handler)

# Обработчик для записи логов в файл
file_handler = RotatingFileHandler('logs/bot.log', maxBytes=5*1024*1024, backupCount=3)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(file_handler)