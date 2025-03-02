from datetime import datetime, timedelta
import os
import logging
import requests
import asyncio
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    func,
    create_engine,
)

from bot.routers.admin_router_sending_message import send_error_report
from initialization.vdsina_processor_init import vdsina_processor
from bot.utils.send_message import send_message_subscription_expired
from database.models import Base, VpnKey, Server, User
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
        self._server_creation_lock = asyncio.Lock()

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
            self, user_id, key, period, server_id, protocol_type="outline", is_trial_key=False
    ) -> bool:
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
        start_date = datetime.now().replace(minute=0, second=0, microsecond=0)

        if is_trial_key:
            expiration_date = (start_date + timedelta(days=2)).replace(
                minute=0, second=0, microsecond=0
            )
        else:
            period_months = int(period.split()[0])
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

            if is_trial_key is True:
                if user.use_trial_period is True:
                    return False
                else:
                    user.use_trial_period = True

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
        return True
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
        Если такого сервера нет, создает новый, гарантируя, что одновременно создается не более одного сервера.
        :param protocol_type: Например, "outline" или "vless"
        :return: Объект сервера
        """
        async with self._server_creation_lock:
            with self.session_scope() as session:
                count_servers = session.query(Server).count()
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

                    new_server, server_ip, server_password = await self.create_new_server(count_servers)

                    if not new_server:
                        await send_error_report("Ошибка при создании нового сервера")
                        logger.error("Ошибка при создании нового сервера")
                        return None

                    new_server_db = self.add_server(new_server, protocol_type, server_ip, server_password)
                    processor = await get_processor(protocol_type.lower())
                    result = await processor.setup_server(new_server_db)
                    if not result:
                        await send_error_report("Ошибка при настройке сервера {protocol_type}")
                        logger.error(f"Ошибка при настройке сервера типа {protocol_type}")
                        return None
                    server = new_server_db

                self.increment_server_user_count(server.id)
                server = self.get_server_by_id(server.id)
                return server

    def get_server_info(self, server_id):
        """
        Запрашивает информацию о сервере по его ID.
        :param server_id:
        :return:
        """
        url = f"https://userapi.vdsina.com/v1/server/{server_id}"
        headers = {"Authorization": f"Bearer {os.getenv('VDSINA_TOKEN')}"}

        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get("status") == "ok":
            return data.get("data", {})
        return None

    async def wait_for_server_ready(self, server_id, timeout=300):
        """
        Ожидает, пока сервер станет активным.
        :param server_id: ID сервера
        :param timeout: Максимальное время ожидания в секундах
        :return: True, если сервер активен, иначе False
        """
        for _ in range(timeout // 5):  # Проверяем каждые 5 секунд
            server_data = self.get_server_info(server_id)
            if server_data and server_data.get("status") == "active":
                return True
            logger.info("Сервер еще не активен, ждем...")
            await asyncio.sleep(5)  # Ждем 5 секунд перед следующей проверкой
        logger.error("Таймаут ожидания сервера!")
        await send_error_report("Таймаут ожидания сервера!")
        return False

    def get_server_ip(self, server_id):
        """
        Запрашивает информацию о сервере по его ID.
        :param server_id:
        :return: IP-адрес сервера
        """
        url = f"https://userapi.vdsina.com/v1/server/{server_id}"
        headers = {"Authorization": f"Bearer {os.getenv('VDSINA_TOKEN')}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("status") == "ok":
            server_data = data.get("data", {})
            ip_list = server_data.get("ip", [])
            if ip_list:
                return ip_list[0].get("ip")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_error_report("Ошибка при получении IP сервера"))
        return None

    def get_server_password(self, server_id):
        """
        Получает пароль сервера по его ID.
        :param server_id:
        :return: Пароль сервера
        """
        url = f"https://userapi.vdsina.com/v1/server.password/{server_id}"
        headers = {"Authorization": f"Bearer {os.getenv('VDSINA_TOKEN')}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("status") == "ok":
            server_data = data.get("data", {})
            password = server_data.get("password", [])
            if password:
                return password
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_error_report("Ошибка при получении пароля сервера"))
        return None

    async def create_new_server(self, count_servers):
        """
        Создает новый сервер на vdSina.
        :return: Объект нового сервера
        """
        template_id = 31  # ID шаблона для сервера
        logger.info("Отправляем запрос на vdSina для создания нового сервера")
        new_server = await vdsina_processor.create_new_server(
            name="Server-" + str(count_servers + 1),
            datacenter_id=1,
            server_plan_id=1,
            template_id=template_id,
            ip4=1,
            email=os.getenv("VDSINA_EMAIL"),
            password=os.getenv("VDSINA_PASSWORD"),
        )
        if not new_server or new_server.get("status") != "ok":
            await send_error_report("Ошибка при создании нового сервера")
            logger.error("Ошибка при создании нового сервера")
            return None
        server_id = new_server["data"]["id"]
        logger.info(f"Создан новый сервер с ID: {server_id}")
        is_ready = await self.wait_for_server_ready(server_id)
        if not is_ready:
            await send_error_report("Сервер не стал активным, невозможно получить IP и пароль")
            logger.error("Сервер не стал активным, невозможно получить IP и пароль")
            return None
        server_ip = self.get_server_ip(server_id)
        server_password = self.get_server_password(server_id)
        logger.info(f"Сервер готов: IP={server_ip}, Пароль={server_password}")
        return new_server, server_ip, server_password

    def add_server(self, server_data: dict, protocol_type: str, server_ip: str, server_password: str) -> Server:
        """
         Добавляет информацию о сервере в базу данных.
        :param server_data: Словарь с данными сервера.
        :param protocol_type: Тип протокола (например, "Outline").
        :return: Объект нового сервера.
        """
        with self.session_scope() as session:
            new_server = Server(
                ip=server_ip,
                password=server_password,
                api_url="https://userapi.vdsina.ru",
                cert_sha256=server_data.get("cert_sha256", ""),
                cnt_users=0,
                protocol_type=protocol_type,
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
                loop = asyncio.get_event_loop()
                loop.run_until_complete(send_error_report("Ошибка при получении ID сервера"))
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
                loop = asyncio.get_event_loop()
                loop.run_until_complete(send_error_report("Ошибка при получении сервера по ID"))
                logger.error(f"Сервер с id {server_id} не найден.")
                raise ValueError("Нет сервера с переданным id")
            return server

    def increment_server_user_count(self, server_id: int) -> Server:
        with self.session_scope() as session:
            server = session.query(Server).filter_by(id=server_id).one()
            server.cnt_users += 1
            session.commit()
            session.refresh(server)
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

    async def check_count_keys_on_servers(self):
        """
        Асинхронная проверка числа клиентов на серверах
        - Если на всех серверах какого-то типа > 159 клиентов, то поднимаем новый сервер соответствующего типа
        :return:
        """
        from utils.get_processor import get_processor
        async with self._server_creation_lock:
            with self.session_scope() as session:
                count_servers = session.query(Server).count()
                server_types = ("outline", "vless")
                for protocol_type in server_types:
                    servers = (
                        session.query(Server).filter_by(protocol_type=protocol_type).all()
                    )
                    all_servers_full = all(server.cnt_users >= 159 for server in servers)
                    if all_servers_full:
                        logger.info(
                            f"Все сервера типа {protocol_type} имеют не менее 159 ключей"
                        )
                        new_server, server_ip, server_password = await self.create_new_server(count_servers)
                        logger.info(f"Подняли новый сервер типа {protocol_type}")
                        new_server = self.add_server(new_server, protocol_type, server_ip, server_password)
                        logger.info(f"Записали данные нового сервера в БД")
                        processor = await get_processor(protocol_type)
                        logger.info(f"Передаем сервер в setup_server: {new_server}")
                        result = await processor.setup_server(new_server)
                        if not result:
                            logger.error(f"Ошибка при настройке сервера типа {protocol_type}")
                            return
                        logger.info(f"Настроили сервер типа {protocol_type}")

    async def check_and_update_key_data_limit(self):
        from utils.get_processor import get_processor

        with self.session_scope() as session:
            keys = session.query(VpnKey).all()
            for key in keys:
                now = datetime.now()
                if key.expiration_date >= now:
                    processor = await get_processor(key.protocol_type)
                    key_info = await processor.get_key_info(
                        key.key_id, server_id=key.server_id
                    )
                    logger.info("Обновляем лимит")
                    await processor.update_data_limit(
                        key.key_id,
                        key_info.data_limit
                        + (key_info.used_bytes - key.used_bytes_last_month),
                        server_id=key.server_id,
                        key_name=key.name,
                    )
                    key.used_bytes_last_month = key_info.used_bytes

    def update_server_by_id(self, server_id, api_url, cert_sha256):
        with self.session_scope() as session:
            # Берём сервер непосредственно в этой же сессии
            server = session.query(Server).filter_by(id=server_id).one()
            server.api_url = api_url
            server.cert_sha256 = cert_sha256
            session.commit()
            # При необходимости можно сделать session.refresh(server)
            session.refresh(server)
            logger.info(
                f"Сервер {server_id} успешно обновлен, server.api_url={api_url}, server.cert_sha256={cert_sha256}")
