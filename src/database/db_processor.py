from aiogram.fsm.storage.base import StorageKey
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
import asyncio
import aiocron
import os
from contextlib import contextmanager

from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import (
    func,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    create_engine,
    Integer,
)

from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.vdsina_processor_init import vdsina_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.utils.get_processor import get_processor
from bot.utils.send_message import send_message_subscription_expired

from logger.logging_config import setup_logger
from dotenv import load_dotenv

logger = setup_logger()
Base = declarative_base()
load_dotenv()
vdsina_password = os.getenv("VDSINA_PASSWORD")


class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных
        self.engine = create_engine("sqlite:///database/vpn_users.db", echo=True)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init_db(self):
        """Синхронная инициализация базы данных."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Создает и возвращает новую сессию."""
        return self.Session()

    @contextmanager
    def session_scope(self):
        """
        Контекстный менеджер для работы с сессией.
        Обеспечивает автоматический коммит или откат транзакции.
        :return: Сессия
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()


    def get_key_by_id(self, key_id: str):
        with self.session_scope() as session:
            return session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    def get_vpn_type_by_key_id(self, key_id: str) -> str:
        """
        Возвращает тип протокола VPN по ID ключа.
        :param key_id:
        :return:
        """
        with self.session_scope() as session:
            key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
            if key:
                return key.protocol_type
            else:
                logger.error(f"Ошибка при получении информации о ключе {key_id}")
                return None

    def update_database_with_key(
            self, user_id, key, period, server_id, protocol_type="Outline"
    ):
        """
        Обновляет базу данных новым ключом.
        :param user_id:
        :param key:
        :param period:
        :param server_id:
        :param protocol_type:
        :return:
        """
        user_id_str = str(user_id)
        period_months = int(period.split()[0])
        start_date = datetime.now().replace(minute=0, second=0, microsecond=0)
        expiration_date = (start_date + timedelta(days=30 * period_months)).replace(
            minute=0, second=0, microsecond=0
        )
        with self.session_scope() as session:
            user = session.query(DbProcessor.User).filter_by(user_telegram_id=user_id_str).first()
            if not user:
                user = DbProcessor.User(
                    user_telegram_id=user_id_str,
                    subscription_status="active",
                    use_trial_period=False,
                )
                session.add(user)
                session.commit()

            new_key = DbProcessor.Key(
                key_id=key.key_id,
                user_telegram_id=user_id_str,
                expiration_date=expiration_date,
                start_date=start_date,
                protocol_type=protocol_type,
                name=key.name,
                server_id=server_id,
            )
            session.add(new_key)
            session.commit()

    async def get_expired_keys_by_user_id(self, user_id):
        """
        Возвращает словарь с истекшими ключами пользователя.
        :param user_id:
        :return:
        """
        expired_keys = {}
        with self.session_scope() as session:
            keys = session.query(DbProcessor.Key).filter_by(user_telegram_id=user_id).all()
            for key in keys:
                time_remaining = key.expiration_date - datetime.now()
                if time_remaining < timedelta(days=4):
                    expired_keys[key.key_id] = (
                        key.name,
                        time_remaining.days + 1, # +1 день, чтобы учесть текущий день
                    )
            return expired_keys

    async def check_db(self):
        """
        Асинхронная проверка базы данных на истекшие ключи.
        - Если ключ истекает через 3 дня, отправляется уведомление.
        - Если ключ истекает сегодня, он удаляется из базы данных.
        :return:
        """
        now = datetime.now()
        with self.session_scope() as session:
            users = session.query(DbProcessor.User).all()
            for user in users:
                logger.info(f"Проверка пользователя: {user.user_telegram_id}")
                expiring_keys = {}
                for key in user.keys:
                    time_diff = key.expiration_date - now
                    if timedelta(days=0) < time_diff < timedelta(days=4):
                        key.remembering = True
                        expiring_keys[key.key_id] = (key.name, time_diff.days + 1)
                    elif key.expiration_date + timedelta(days=1) < now:
                        processor = await get_processor(key.protocol_type.lower())
                        server = session.query(DbProcessor.Server).filter_by(id=key.server_id).first()
                        processor.delete_key(key.key_id, server_id=key.server_id)
                        session.delete(key)
                        if server:
                            server.cnt_users = max(0, server.cnt_users - 1)
                        session.commit()
                    elif key.expiration_date < now:
                        expiring_keys[key.key_id] = (key.name, 0)
                if expiring_keys:
                    await send_message_subscription_expired(user.user_telegram_id, expiring_keys)

    async def get_server_with_min_users(self, protocol_type: str):
        """
        Выбирает сервер с минимальным количеством пользователей для указанного протокола.
        Если такой сервер отсутствует, создается новый сервер.
        :param protocol_type:
        :return:
        """
        with self.session_scope() as session:
            server = (
                session.query(DbProcessor.Server)
                .filter(
                    func.lower(DbProcessor.Server.protocol_type)
                    == protocol_type.lower()
                )
                .filter(DbProcessor.Server.cnt_users < 160)
                .order_by(DbProcessor.Server.cnt_users.asc())
                .with_for_update()  # Блокируем строку для изменения
                .first()
            )

            if not server:
                logger.info(f"Сервера с протоколом {protocol_type} не найдено.")
                template_id = 31 # ID шаблона для сервера
                new_server = await vdsina_processor.create_new_server(
                    datacenter_id=1,
                    server_plan_id=1,
                    template_id=template_id,
                    ip4=1,
                    email="asadullinam@yandex.ru",
                    password=vdsina_password,
                )
                if not new_server:
                    logger.error("Ошибка при создании нового сервера")
                    return None
                new_server_db = self.add_server(new_server, protocol_type)
                match protocol_type.lower():
                    case "outline":
                        await async_outline_processor.setup_server_outline(
                            new_server_db
                        )
                    case "vless":
                        await vless_processor.setup_server_vless(new_server_db)
                server = new_server_db
            server.cnt_users += 1
            session.commit()
            session.refresh(server)
            return server

    def add_server(self, server_data: dict, protocol_type: str):
        """
         Добавляет информацию о сервере в базу данных.
        :param server_data: Словарь с данными сервера.
        :param protocol_type: Тип протокола (например, "Outline").
        :return: Объект нового сервера.
        """
        ip_list = server_data.get("ip", [])
        primary_ip = ip_list[0].get("ip") if ip_list and isinstance(ip_list, list) and ip_list else None
        with self.session_scope() as session:
            new_server = DbProcessor.Server(
                ip=primary_ip,
                password=server_data.get("password", ""),
                api_url="https://userapi.vdsina.ru",
                cert_sha256=server_data.get("cert_sha256", ""),
                cnt_users=0,
                protocol_type=server_data.get("protocol_type", "outline"),
            )
            session.add(new_server)
            session.commit()
            session.refresh(new_server)
            logger.info(f"Сервер {new_server.id} успешно добавлен в БД.")
            return new_server
    def get_server_id_by_key_id(self, key_id):
        """
        Возвращает ID сервера по ID ключа.
        :param key_id:
        :return: ID сервера
        """
        with self.session_scope() as session:
            key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
            if key:
                return key.server_id
            else:
                logger.error(f"Ошибка при получении информации о ключе {key_id}")
                return None

    def get_server_by_id(self, server_id: str):
        """
        Возвращает сервер по ID.
        :param server_id:
        :return:
        """
        with self.session_scope() as session:
            server = session.query(DbProcessor.Server).filter_by(id=server_id).first()
            if server:
                logger.info(f"Найден сервер с id: {server_id}")
            else:
                logger.error(f"Сервер с id {server_id} не найден.")
            return server

    def rename_key(self, key_id: str, new_name: str) -> bool:
        """
        Изменяет имя ключа.
        :param key_id:
        :param new_name:
        :return:
        """
        with self.session_scope() as session:
            key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
            if not key:
                logger.warning(f"Ключ с ID {key_id} не найден.")
                return False
            key.name = new_name
            logger.info(f"Имя ключа с ID {key_id} изменено на {new_name}")
            return True

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
        user = relationship("User", back_populates="keys")
        expiration_date = Column(DateTime)  # Дата окончания подписки
        start_date = Column(DateTime)  # Дата начала подписки
        protocol_type = Column(String, default="Outline")
        name = Column(String, default=None)
        remembering_before_exp = Column(
            Boolean, default=False
        )  # напомнить о продлении 1 раз
        server_id = Column(String, ForeignKey("servers.id"))  # Связь с сервером
        server = relationship("Server", back_populates="keys")

    class Server(Base):
        __tablename__ = "servers"
        id = Column(Integer, primary_key=True, autoincrement=True)
        ip = Column(String, default=None)
        password = Column(String, default=None)
        api_url = Column(String, default=None)
        cert_sha256 = Column(String, default=None)
        cnt_users = Column(Integer, default=0)
        protocol_type = Column(String, default="Outline")
        keys = relationship("Key", back_populates="server")

        def save(self):
            """
            Сохраняет изменения объекта в базе данных.
            Использует глобальный экземпляр db_processor для получения сессии.
            """
            with self.session_scope() as session:
                session.merge(self)