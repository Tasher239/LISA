import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from tempfile import template

from sqlalchemy import func

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    create_engine,
    Integer,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.initialization.vdsina_processor_init import vdsina_processor

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

    def get_key_by_id(self, key_id: str):
        session = self.get_session()
        try:
            return session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
        except Exception as e:
            logger.error(f"Ошибка при получении ключа {key_id}: {e}")
            return None
        finally:
            session.close()

    def get_vpn_type_by_key_id(self, key_id: str) -> str:
        session = self.get_session()
        try:
            key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
            return key.protocol_type
        except Exception as e:
            logger.error(f"Ошибка при получении информации о ключе {key_id}: {e}")
            raise
        finally:
            session.close()

    def update_database_with_key(
        self, user_id, key, period, server_id, protocol_type="Outline"
    ):
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
                name=key.name,
                server_id=server_id,
            )
            session.add(new_key)
            session.commit()

        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}")
            raise
        finally:
            session.close()

    async def get_expired_keys_by_user_id(self, user_id):
        session = self.get_session()
        keys = session.query(DbProcessor.Key).filter_by(user_telegram_id=user_id).all()

        expired_keys = {}
        for key in keys:
            if key.expiration_date - datetime.now() < timedelta(days=4):
                expired_keys[key.key_id] = (
                    key.name,
                    (key.expiration_date - datetime.now()).days + 1,
                )
        return expired_keys

    async def check_db(self, dp):
        while True:
            session = self.get_session()
            try:
                users = session.query(DbProcessor.User).all()
                for user in users:
                    print(f"Проверка пользователя: {user.user_telegram_id}")
                    expiring_keys = {}  # {key_id: (key_name, expiration_time)}
                    for key in user.keys:
                        # ключ будет действовать меньше 3х дней
                        if (
                            timedelta(days=0)
                            < key.expiration_date - datetime.now()
                            < timedelta(days=4)
                        ):
                            key.remembering = True
                            expiring_keys[key.key_id] = (
                                key.name,
                                (key.expiration_date - datetime.now()).days + 1,
                            )
                        # ключ больше не работает
                        elif key.expiration_date < datetime.now():
                            # Устанавливаем состояние "extension"
                            expiring_keys[key.key_id] = (key.name, 0)
                        # тухлый ключ лежит в бд 1 день - удаляем из бд
                        elif datetime.now() > key.expiration_date + timedelta(days=1):
                            session.delete(key)
                            session.commit()
                    if expiring_keys:
                        await send_message_subscription_expired(
                            user.user_telegram_id, expiring_keys
                        )
            except Exception as e:
                logger.error(f"Ошибка проверки базы данных: {e}")
                raise
            await asyncio.sleep(
                60 * 60 * 24
            )  # каждые 24 ч перенесена в конец чтобы 1 раз пробегаться при запуске бота

    async def get_server_with_min_users(self, protocol_type: str):
        session = self.get_session()
        try:
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
                print("Сервера нет")
                # если сервера нет, нужно подянть новый
                # идем в вдсина процессор и запрашиваем новый сервер
                template_id = 0
                match protocol_type.lower():
                    case "outline":
                        template_id = 31
                    case "vless":
                        template_id = 31
                new_server = await vdsina_processor.create_new_server(
                    datacenter_id=1,
                    server_plan_id=1,
                    template_id=template_id,
                    ip4=1,
                    email="asadullinam@yandex.ru",
                    password="piDhij-tevtat-9rokgy",
                )

                if not new_server:
                    logger.error("Ошибка при создании нового сервера")
                    return None
                new_server_db = self.add_server(new_server, protocol_type)
                match protocol_type.lower():
                    case "outline":
                        await async_outline_processor.setup_server_outline(new_server_db)
                    case "vless":
                        await vless_processor.setup_server_vless(new_server_db)

                server = new_server_db

            server.cnt_users += 1
            session.commit()
            session.refresh(server)  # Обновляем объект после коммита
            return server  # Возвращаем объект сервера
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при выборе сервера: {e}")
            return None
        finally:
            session.close()

    def add_server(self, server_data: dict, protocol_type: str):
        """
        Добавляет информацию о сервере в базу данных.
        :param server_data: Словарь с данными сервера, полученными от API.
            Ожидаются следующие поля:
                - "id": идентификатор сервера;
                - "ip": список IP-объектов, где берется первый IP (например, ip[0]["ip"]);
                - "password": пароль (обычно его нужно получать отдельно, здесь может быть пустой строкой);
                - "cnt_users": количество подключенных пользователей (обычно 0);
                - "protocol_type": тип протокола (например, "Outline").
            Остальные поля можно задавать вручную или по умолчанию.
        :return: Объект добавленного сервера или выбрасывается исключение.
        """
        session = self.get_session()
        try:
            ip_list = server_data.get("ip")
            primary_ip = None
            if ip_list and isinstance(ip_list, list) and len(ip_list) > 0:
                primary_ip = ip_list[0].get("ip")
            new_server = DbProcessor.Server(
                ip=primary_ip,
                password=server_data.get(
                    "password", ""
                ),  # Пароль, если доступен (иначе пустая строка)
                api_url="https://userapi.vdsina.ru",  # URL можно задать статически
                cert_sha256=server_data.get(
                    "cert_sha256", ""
                ),  # Это поле не возвращается API, задаем по умолчанию
                cnt_users=server_data.get(
                    "cnt_users", 0
                ),  # Обычно сервер создается с 0 пользователями
                protocol_type=server_data.get("protocol_type", "Outline"),
            )
            session.add(new_server)
            session.commit()
            session.refresh(new_server)  # Обновляем объект после коммита
            logger.info(f"Сервер {new_server.id} успешно добавлен в БД.")
            return new_server

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при добавлении сервера: {e}")
        finally:
            session.close()

    def get_server_id_by_key_id(self, key_id):
        session = self.get_session()
        try:
            key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
            return key.server_id
        except Exception as e:
            logger.error(f"Ошибка при получении сервера по ключу {key_id}: {e}")
            return None
        finally:
            session.close()

    def get_server_by_id(self, server_id: str):
        session = self.get_session()
        try:
            server = session.query(DbProcessor.Server).filter_by(id=server_id).first()
            logger.info(f"искали ключ по id: {server_id}")
            return server
        except Exception as e:
            logger.error(f"Ошибка при получении сервера {server_id}: {e}")
            return None

    def rename_key(self, key_id: str, new_name: str) -> bool:
        with self.get_session() as session:
            try:
                key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
                if not key:
                    logger.warning(f"Ключ с ID {key_id} не найден.")
                    return False

                key.name = new_name
                session.commit()
                logger.info(f"Имя ключа с ID {key_id} изменено на {new_name}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Ошибка при изменении имени ключа {key_id}: {e}")
                return False

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
