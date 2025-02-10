# app/shared.py

from app.database import User, db_session, encryption_manager  # Импортируем необходимые компоненты из database.py
from app.contexts import UserContext  # Импортируем UserContext

# Класс для управления состоянием бота
class BotStateManager:
    def __init__(self):
        self.active_users = {}  # Словарь для отслеживания состояния торговли для каждого пользователя
    
    def start(self, user_id: int):
        """Запускает торговлю для указанного пользователя."""
        self.active_users[user_id] = True
    
    def stop(self, user_id: int):
        """Останавливает торговлю для указанного пользователя."""
        if user_id in self.active_users:
            self.active_users[user_id] = False
    
    def is_trading_active(self, user_id: int) -> bool:
        """Проверяет, активна ли торговля для указанного пользователя."""
        return self.active_users.get(user_id, False)

bot_state_manager = BotStateManager()

# Функция для получения или создания контекста пользователя
def get_user_context(user_id: int) -> 'UserContext':
    """
    Получает или создает контекст пользователя.
    
    :param user_id: Уникальный идентификатор пользователя.
    :return: Экземпляр UserContext.
    """
    with db_session() as session:  # Создаем новую сессию через вызов db_session()
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            user = User(id=user_id)
            session.add(user)
            session.commit()

    # Создаем экземпляр UserContext на основе данных из базы данных
    return UserContext(user_id)