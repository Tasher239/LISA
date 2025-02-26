from datetime import datetime, timedelta
import os
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    func,
    create_engine,
)


from initialization.vdsina_processor_init import vdsina_processor
from bot.utils.send_message import send_message_subscription_expired
from database.models import Base, VpnKey, Server, User
from logger.logging_config import setup_logger
from dotenv import load_dotenv

logger = setup_logger()

load_dotenv()


class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных
        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )  # Получаем путь к текущему файлу (db_processor_init.py)
        db_path = os.path.join(
            base_dir, "..", "database", "vpn_users.db"
        )  # Поднимаемся на уровень выше
        db_uri = f"sqlite:///{os.path.abspath(db_path)}"  # Создаем абсолютный путь

        self.engine = create_engine(db_uri, echo=True)
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

    def get_key_by_id(self, key_id: str) -> VpnKey | None:
        """Возвращает объект ключа (VpnKey) по его ID или None, если ключ не найден."""
        with self.session_scope() as session:
            return session.query(VpnKey).filter_by(key_id=key_id).first()

    def get_vpn_type_by_key_id(self, key_id: str) -> str:
        """
        Возвращает тип протокола VPN по ID ключа.
        :param key_id:
        :return:
        """
        with self.session_scope() as session:
            key = session.query(VpnKey).filter_by(key_id=key_id).first()
            if key:
                return key.protocol_type
            else:
                logger.error(f"Ошибка при получении информации о ключе {key_id}")
                return None

    def update_database_with_key(
        self, user_id, key, period, server_id, protocol_type="Outline"
    ) -> None:
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
            user = session.query(User).filter_by(user_telegram_id=user_id_str).first()
            if not user:
                user = User(
                    user_telegram_id=user_id_str,
                    subscription_status="active",
                    use_trial_period=False,
                )
                session.add(user)
                session.commit()

            new_key = VpnKey(
                key_id=key.key_id,
                user_telegram_id=user_id_str,
                expiration_date=expiration_date,
                start_date=start_date,
                protocol_type=protocol_type,
                name=key.name,
                server_id=server_id,
            )
            session.add(new_key)
            # session.commit() <- возможно не нужно тк юзаем контекстный менеджер

    async def get_expired_keys_by_user_id(self, user_id) -> dict[str, tuple[str, int]]:
        """
        Возвращает словарь с истекшими ключами пользователя.
        :param user_id:
        :return:
        """
        expired_keys = {}
        with self.session_scope() as session:
            keys = session.query(VpnKey).filter_by(user_telegram_id=user_id).all()
            for key in keys:
                time_remaining = key.expiration_date - datetime.now()
                if time_remaining < timedelta(days=4):
                    expired_keys[key.key_id] = (
                        key.name,
                        time_remaining.days + 1,  # +1 день, чтобы учесть текущий день
                    )
            return expired_keys

    async def check_db(self):
        """
        Асинхронная проверка базы данных на истекшие ключи.
        - Если ключ истекает через 3 дня, отправляется уведомление.
        - Если ключ истекает сегодня, он удаляется из базы данных.
        :return:
        """
        with self.session_scope() as session:
            users = session.query(User).all()

            # Обрабатываем каждого пользователя
            for user in users:
                expiring_keys = await self._check_user_keys(user, session)

                if expiring_keys:
                    # Отправляем уведомления об истекающих ключах
                    await send_message_subscription_expired(
                        user.user_telegram_id, expiring_keys
                    )

    async def _check_user_keys(self, user, session):
        """
        Проверяет ключи пользователя на истечение и выполняет соответствующие действия.
        :param user: Объект пользователя
        :param session: Сессия базы данных
        :return: Словарь с истекающими ключами для уведомления
        """
        expiring_keys = {}
        now = datetime.now()
        for key in user.keys:
            time_diff = key.expiration_date - now

            if timedelta(days=-2) < time_diff < timedelta(days=4):
                # Ключ будет действителен не более 3х дней или уже истек
                expiring_keys[key.key_id] = (
                    key.name,
                    max(time_diff, timedelta(days=0)).days + 1,
                )
            elif key.expiration_date < now:
                # Если ключ истек более 2х дней назад
                await self._delete_expired_key(key, session)
                expiring_keys[key.key_id] = (key.name, 0)

        return expiring_keys

    @staticmethod
    async def _delete_expired_key(key, session):
        """
        Удаляет истекший ключ из базы данных.
        :param key: Ключ для удаления
        :param session: Сессия базы данных
        """
        from utils import get_processor

        processor = await get_processor(key.protocol_type.lower())
        processor.delete_key(key.key_id, server_id=key.server_id)
        session.delete(key)

        # Обновляем количество пользователей на сервере
        key.server.cnt_users = max(0, key.server.cnt_users - 1)

    async def get_server_with_min_users(self, protocol_type: str) -> Server:
        """
        Выбирает сервер с минимальным количеством пользователей для указанного протокола.
        Если такой сервер отсутствует, создается новый сервер.
        :param protocol_type:
        :return:
        """
        with self.session_scope() as session:
            server = (
                session.query(Server)
                .filter(func.lower(Server.protocol_type) == protocol_type.lower())
                .filter(Server.cnt_users < 160)
                .order_by(Server.cnt_users.asc())
                .with_for_update()  # Блокируем строку для изменения
                .first()
            )
            from utils.get_processor import get_processor

            if not server:
                logger.info(f"Сервера с протоколом {protocol_type} не найдено.")
                template_id = 31  # ID шаблона для сервера
                new_server = await vdsina_processor.create_new_server(
                    datacenter_id=1,
                    server_plan_id=1,
                    template_id=template_id,
                    ip4=1,
                    email=os.getenv("VDSINA_EMAIL"),
                    password=os.getenv("VDSINA_PASSWORD"),
                )

                if not new_server:
                    logger.error("Ошибка при создании нового сервера")
                    return None

                new_server_db = self.add_server(new_server, protocol_type)
                processor = await get_processor(protocol_type.lower())
                await processor.setup_server(new_server_db)
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
        primary_ip = (
            ip_list[0].get("ip")
            if ip_list and isinstance(ip_list, list) and ip_list
            else None
        )

        with self.session_scope() as session:
            new_server = Server(
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

    def get_server_id_by_key_id(self, key_id) -> int:
        """
        Возвращает ID сервера по ID ключа.
        :param key_id:
        :return: ID сервера
        """
        with self.session_scope() as session:
            key = session.query(VpnKey).filter_by(key_id=key_id).first()
            if key:
                return key.server_id
            else:
                logger.error(f"Ошибка при получении информации о ключе {key_id}")
                return None

    def get_server_by_id(self, server_id: str) -> Server:
        """
        Возвращает сервер по ID.
        :param server_id:
        :return:
        """
        with self.session_scope() as session:
            server = session.query(Server).filter_by(id=server_id).first()
            if server:
                logger.info(f"Найден сервер с id: {server_id}")
            else:
                logger.error(f"Сервер с id {server_id} не найден.")
                raise ValueError("Нет сервера с переданным id")
            return server

    def rename_key(self, key_id: str, new_name: str) -> bool:
        """
        Изменяет имя ключа.
        :param key_id:
        :param new_name:
        :return:
        """
        with self.session_scope() as session:
            key = session.query(VpnKey).filter_by(key_id=key_id).first()
            if not key:
                logger.warning(f"Ключ с ID {key_id} не найден.")
                return False
            key.name = new_name
            logger.info(f"Имя ключа с ID {key_id} изменено на {new_name}")
            return True
