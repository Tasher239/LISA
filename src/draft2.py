from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Определяем базовый класс для моделей
Base = declarative_base()


# Модель Users
class User(Base):
    __tablename__ = "users"

    telegram_id = Column(String, primary_key=True)  # Телеграм ID
    subscription_status = Column(String, nullable=False)  # Статус подписки
    keys_lst = relationship("Key", back_populates="user")  # Связь с ключами


# Модель Keys
class Key(Base):
    __tablename__ = "keys"

    key_value = Column(String, primary_key=True)  # Сам ключ
    user_id = Column(
        String, ForeignKey("users.telegram_id"), nullable=False
    )  # ID пользователя
    expiration_date = Column(DateTime, nullable=False)  # Дата окончания действия ключа

    user = relationship("User", back_populates="keys_lst")  # Связь с пользователем


# Создаем подключение к базе данных
engine = create_engine(
    "sqlite:///my_database.db", echo=True
)  # Создаём базу данных SQLite

# Создаем таблицы
Base.metadata.create_all(engine)

# Создаем сессию для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()

# Пример добавления данных
new_user = User(telegram_id="123456789", subscription_status="active")

new_key = Key(
    key_value="some_vpn_key_123",
    user_id="123456789",
    expiration_date=datetime(2025, 12, 31, 23, 59, 59),
)

# Добавление пользователя и ключа в базу данных
session.add(new_user)
session.add(new_key)
session.commit()

# Закрываем сессию
session.close()
