from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    create_engine,
    Table,
    MetaData,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime, timedelta
from src.logger.logging_config import setup_logger

logger = setup_logger()

# Создаем базовый класс для моделей
Base = declarative_base()


class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных
        self.engine = create_engine("sqlite:///vpn_users.db", echo=True)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """Синхронная инициализация базы данных."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Создает и возвращает новую сессию."""
        return self.Session()

    def update_database_with_key(self, user_id, key, period):
        session = self.get_session()
        try:
            user_id_str = str(user_id)
            user = (
                session.query(DbProcessor.User)
                .filter_by(user_telegram_id=user_id_str)
                .first()
            )
            if not user:
                user = DbProcessor.User(
                    user_telegram_id=user_id_str,
                    subscription_status="active",
                    use_trial_period=False,
                )
                session.add(user)
                session.commit()

            period_months = int(period.split()[0])
            start_date = datetime.now()
            expiration_date = start_date + timedelta(days=30 * period_months)
            new_key = DbProcessor.Key(
                key_id=key.key_id,
                user_telegram_id=user_id_str,
                expiration_date=expiration_date,
                start_date=start_date,
            )
            session.add(new_key)
            session.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}")
            raise
        finally:
            session.close()

    # Определение таблицы Users
    class User(Base):
        __tablename__ = "users"
        user_telegram_id = Column(String, primary_key=True)  # Telegram ID пользователя
        subscription_status = Column(String)  # Статус подписки (active/inactive)
        use_trial_period = Column(Boolean)  # Использован ли пробный период
        # Отношение с таблицей Keys (один ко многим)
        keys = relationship("Key", back_populates="user", cascade="all, delete-orphan")

    # Определение таблицы Keys
    class Key(Base):
        __tablename__ = "keys"
        key_id = Column(String, primary_key=True)  # id ключа в outline и бд
        user_telegram_id = Column(
            String, ForeignKey("users.user_telegram_id")
        )  # ID пользователя (ссылка на пользователя)
        # Обратное отношение к таблице Users
        expiration_date = Column(DateTime)  # Дата окончания подписки
        start_date = Column(DateTime)  # Дата начала подписки

        user = relationship("User", back_populates="keys")
