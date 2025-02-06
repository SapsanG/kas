# app/shared.py
import ccxt
from app.database import User, TradeHistory, db_session, encryption_manager  # Импортируем глобальную сессию
from datetime import datetime, timedelta

# Класс для управления состоянием бота
class BotStateManager:
    def __init__(self):
        self.is_running = False

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def is_trading_active(self):
        return self.is_running

# Глобальный экземпляр BotStateManager
bot_state_manager = BotStateManager()

# Класс для хранения параметров бота
class BotParams:
    def __init__(self, profit_percentage=0.3, fall_percentage=1.0, delay_seconds=30, order_size=40):
        self.profit_percentage = profit_percentage
        self.fall_percentage = fall_percentage
        self.delay_seconds = delay_seconds
        self.order_size = order_size
        self.buy_price = None  # Цена последней покупки

    def set_params(self, profit_percentage, fall_percentage, delay_seconds, order_size):
        self.profit_percentage = profit_percentage
        self.fall_percentage = fall_percentage
        self.delay_seconds = delay_seconds
        self.order_size = order_size

# Класс для хранения контекста пользователя
class UserContext:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.bot_params = self.load_user_params()
        self.api_key = None
        self.api_secret = None
        self.buy_executed = {}  # Словарь для отслеживания выполненных покупок по уровням
        self.current_level = 0  # Текущий уровень сетки

    # Загрузка параметров пользователя из базы данных
    def load_user_params(self):
        user = db_session.query(User).filter_by(id=self.user_id).first()  # Используем глобальную сессию
        if user:
            if user.api_key_encrypted and user.api_secret_encrypted:
                self.api_key = encryption_manager.decrypt(user.api_key_encrypted.encode())
                self.api_secret = encryption_manager.decrypt(user.api_secret_encrypted.encode())
            return BotParams(
                profit_percentage=user.profit_percentage,
                fall_percentage=user.fall_percentage,
                delay_seconds=user.delay_seconds,
                order_size=user.order_size
            )
        return BotParams()

    # Сохранение параметров пользователя в базу данных
    def save_user_params(self):
        user = db_session.query(User).filter_by(id=self.user_id).first()  # Используем глобальную сессию
        if not user:
            user = User(id=self.user_id)
            db_session.add(user)
        
        if self.api_key and self.api_secret:
            user.api_key_encrypted = encryption_manager.encrypt(self.api_key).decode()
            user.api_secret_encrypted = encryption_manager.encrypt(self.api_secret).decode()
        
        user.profit_percentage = self.bot_params.profit_percentage
        user.fall_percentage = self.bot_params.fall_percentage
        user.delay_seconds = self.bot_params.delay_seconds
        user.order_size = self.bot_params.order_size
        db_session.commit()  # Сохраняем изменения

    # Установка API-ключей
    def set_api_credentials(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    # Получение экземпляра биржи MEXC
    def get_mexc_instance(self):
        if not self.api_key or not self.api_secret:
            raise ValueError("API-ключи не установлены.")
        return ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
        })

    # Логирование сделки в базу данных
    def log_trade(self, trade_type: str, symbol: str, amount: float, price: float, profit: float):
        trade = TradeHistory(
            user_id=self.user_id,
            trade_type=trade_type,
            symbol=symbol,
            amount=amount,
            price=price,
            profit=profit,
            timestamp=datetime.utcnow()
        )
        db_session.add(trade)
        db_session.commit()

    # Расчет профита за день
    def calculate_profit_today(self):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        trades = db_session.query(TradeHistory).filter(
            TradeHistory.user_id == self.user_id,
            TradeHistory.trade_type == "sell",
            TradeHistory.timestamp >= today_start
        ).all()
        return sum(trade.profit for trade in trades)

    # Расчет профита за период
    def calculate_profit_period(self, days: int):
        period_start = datetime.now() - timedelta(days=days)
        trades = db_session.query(TradeHistory).filter(
            TradeHistory.user_id == self.user_id,
            TradeHistory.trade_type == "sell",
            TradeHistory.timestamp >= period_start
        ).all()
        return sum(trade.profit for trade in trades)

    # Расчет профита за месяц
    def calculate_profit_month(self):
        return self.calculate_profit_period(30)

    # Расчет профита за всё время
    def calculate_profit_total(self):
        trades = db_session.query(TradeHistory).filter(
            TradeHistory.user_id == self.user_id,
            TradeHistory.trade_type == "sell"
        ).all()
        return sum(trade.profit for trade in trades)

# Функция для получения или создания контекста пользователя
def get_user_context(user_id: int) -> UserContext:
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    return user_contexts[user_id]

# Хранилище контекста пользователей
user_contexts = {}