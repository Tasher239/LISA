import asyncio
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from outline_vpn.outline_vpn import OutlineServerErrorException

from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.utils.send_message import send_message_subscription_expired

from logger.logging_config import setup_logger

logger = setup_logger()
Base = declarative_base()


class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных

        self.engine = create_engine("sqlite:///database/vpn_users.db", echo=True)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """Синхронная инициализация базы данных."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Создает и возвращает новую сессию."""
        return self.Session()

    def get_vpn_type_by_key_id(self, kei_id: str) -> str:
        session = self.get_session()
        try:
            key = session.query(DbProcessor.Key).filter_by(key_id=kei_id).first()
            return key.protocol_type
        except Exception as e:
            logger.error(f"Ошибка при получении информации о ключе {kei_id}: {e}")
            raise
        finally:
            session.close()

    def update_database_with_key(self, user_id, key, period, protocol_type="Outline"):
        """Обновляет БД по новому созданному ключу для пользователя"""
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
                protocol_type=protocol_type,
                name=key.name
            )
            session.add(new_key)
            session.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}")
            raise
        finally:
            session.close()

    async def check_db(self, dp):
        while True:
            session = self.get_session()
            try:
                users = session.query(DbProcessor.User).all()
                for user in users:
                    print(f"Проверка пользователя: {user.user_telegram_id}")
                    expiring_keys = {}  # {key_id: (key_name, expiration_time)}
                    for key in user.keys:
                        try:
                            if key.protocol_type == "Outline":
                                key_info = outline_processor.get_key_info(key.key_id)
                            else:
                                key_info = vless_processor.get_key_info(key.key_id)
                        except OutlineServerErrorException as e:
                            logger.warning(
                                f"Ключ {key.key_id} не найден: {e}, удаляю из БД"
                            )
                            session.delete(key)
                            session.commit()
                            continue
                        except Exception as e:
                            logger.error(
                                f"Ошибка при получении информации о ключе {key.key_id}: {e}"
                            )
                            continue
                        if key_info is None:
                            logger.warning(
                                f"Ключ {key.key_id} не найден или пустой, пропускаем"
                            )
                            continue
                        key_name = key_info.name
                        # ключ будет действовать меньше 3х дней
                        if (
                            timedelta(days=0)
                            < key.expiration_date - datetime.now()
                            < timedelta(days=4)
                        ):
                            key.remembering = True
                            expiring_keys[key.key_id] = (
                                key_name,
                                (key.expiration_date - datetime.now()).days + 1,
                            )
                        # ключ больше не работает
                        elif key.expiration_date < datetime.now():
                            # Устанавливаем состояние "extension"
                            expiring_keys[key.key_id] = (key_name, 0)
                        # тухлый ключ лежит в бд 1 день - удаляем из бд
                        elif datetime.now() > key.expiration_date + timedelta(days=1):
                            session.delete(key)
                            session.commit()
                    if expiring_keys:
                        await send_message_subscription_expired(user, expiring_keys)
            except Exception as e:
                logger.error(f"Ошибка проверки базы данных: {e}")
                raise
            await asyncio.sleep(
                60 * 60 * 24
            )  # каждые 24 ч перенесена в конец чтобы 1 раз пробегаться при запуске бота

    # Определение таблицы Users
    class User(Base):
        __tablename__ = "users"
        user_telegram_id = Column(String, primary_key=True)  # Telegram ID пользователя
        subscription_status = Column(String)  # Статус подписки (active/inactive)
        use_trial_period = Column(Boolean)  # Использован ли пробный период
        # Отношение с таблицей Keys: один ко многим
        keys = relationship("Key", back_populates="user", cascade="all, delete-orphan")

    # Определение таблицы Keys
    class Key(Base):
        __tablename__ = "keys"
        key_id = Column(String, primary_key=True)  # id ключа в outline или vless и бд
        user_telegram_id = Column(
            String, ForeignKey("users.user_telegram_id")
        )  # ID пользователя (ссылка на пользователя)
        # Обратное отношение к таблице Users
        expiration_date = Column(DateTime)  # Дата окончания подписки
        start_date = Column(DateTime)  # Дата начала подписки
        user = relationship("User", back_populates="keys")
        protocol_type = Column(String, default="Outline")
        name = Column(String, default=None)
        remembering_before_exp = Column(
            Boolean, default=False
        )  # напомнить о продлении 1 раз
