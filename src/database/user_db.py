from sqlalchemy import create_engine, Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

# Создаем базовый класс для моделей
Base = declarative_base()

class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных
        self.engine = create_engine('sqlite:///vpn_users.db', echo=True)
        # Создаем сессию для работы с базой данных
        self.Session = sessionmaker(bind=self.engine)

        # Создание всех таблиц в базе данных (если они еще не существуют)
        Base.metadata.create_all(self.engine)

    # Определение таблицы Users
    class User(Base):
        __tablename__ = 'users'

        user_telegram_id = Column(String, primary_key=True)  # Telegram ID пользователя
        subscription_status = Column(String)  # Статус подписки (active/inactive)
        use_trial_period = Column(Boolean)  # Использован ли пробный период

        # Отношение с таблицей Keys (один ко многим)
        keys = relationship('Key', back_populates='user', cascade="all, delete-orphan")


    # Определение таблицы Keys
    class Key(Base):
        __tablename__ = 'keys'

        key_id = Column(String, primary_key=True)  # Сам ключ для VPN
        user_telegram_id = Column(String, ForeignKey('users.user_telegram_id'))  # ID пользователя (ссылка на пользователя)

        # Обратное отношение к таблице Users
        user = relationship('User', back_populates='keys')


