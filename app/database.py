# app/database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
from config.config import DATABASE_URL  # Импортируем URL базы данных
from datetime import datetime

# Создание базового класса для моделей
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # Telegram ID
    api_key_encrypted = Column(String)      # Зашифрованный API-ключ (хранится как строка)
    api_secret_encrypted = Column(String)   # Зашифрованный API-секрет (хранится как строка)
    profit_percentage = Column(Float, default=0.3)  # Процент прибыли
    fall_percentage = Column(Float, default=1.0)    # Процент падения
    delay_seconds = Column(Integer, default=30)     # Задержка между ордерами
    order_size = Column(Float, default=40)          # Размер ордера

# Модель истории торговли
class TradeHistory(Base):
    __tablename__ = 'trade_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)  # Telegram ID пользователя
    trade_type = Column(String)  # Тип сделки (buy/sell)
    symbol = Column(String)  # Торговая пара
    amount = Column(Float)  # Количество валюты
    price = Column(Float)  # Цена сделки
    profit = Column(Float)  # Прибыль от сделки
    timestamp = Column(DateTime, default=datetime.utcnow)  # Время выполнения сделки

# Функция для создания подключения к базе данных
def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

# Глобальный sessionmaker
Session = init_db()  # Создаем sessionmaker
db_session = Session  # Оставляем как sessionmaker

# Шифрование/дешифрование данных
class EncryptionManager:
    def __init__(self, key: bytes):
        self.cipher_suite = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Шифрует данные и возвращает их в виде строки (base64).
        :param data: Строка для шифрования.
        :return: Зашифрованные данные в формате строки.
        """
        if not isinstance(data, str):
            raise ValueError("Данные для шифрования должны быть строкой.")
        return self.cipher_suite.encrypt(data.encode()).decode()  # Возвращаем строку
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Дешифрует данные из строки (base64) обратно в строку.
        :param encrypted_data: Зашифрованные данные в формате строки.
        :return: Расшифрованная строка.
        """
        if not isinstance(encrypted_data, str):
            raise ValueError("Зашифрованные данные должны быть строкой.")
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()  # Преобразуем строку в байты перед дешифрованием

# Чтение ключа шифрования из файла
with open("encryption_key.txt", "rb") as key_file:
    encryption_key = key_file.read()

# Глобальный менеджер шифрования
encryption_manager = EncryptionManager(encryption_key)