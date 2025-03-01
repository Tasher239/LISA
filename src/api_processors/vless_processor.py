from coolname import generate_slug
from dotenv import load_dotenv
import requests
import asyncssh
import asyncio
import urllib3
import json
import uuid
import os
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from api_processors.base_processor import BaseProcessor
from api_processors.key_models import VlessKey


logger = logging.getLogger(__name__)

load_dotenv()

NAME_VPN_CONFIG = "MyNewInbound"


class VlessProcessor(BaseProcessor):
    def __init__(self, ip, password):
        self.ip = None
        self.sub_port = None
        self.port_panel = None
        self.host = None
        self.data = None
        self.ses = None
        self.con = None
        self.server_id = None

    @staticmethod
    def create_server_session_by_id(func):
        """
        Декоратор для создания сессии с сервером по переданному ID сервера.

        :param func: Функция, которую декоратор оборачивает.

        :return: Результат выполнения функции, обернутой декоратором.

        Алгоритм работы:
        1. Проверяет, существует ли уже сессия.
        2. Если сессия не существует, извлекает `server_id` из аргументов функции.
        3. Если `server_id` не передан, выбрасывает исключение.
        4. Использует `db_processor` для получения данных о сервере по ID.
        5. Если сервер не найден, выбрасывает исключение.
        6. Инициализирует параметры подключения (IP, порт, данные).
        7. Создает новую сессию с помощью `requests.Session`.
        8. Выполняет исходную функцию с аргументами.
        9. В случае ошибки при установке соединения выбрасывает исключение.
        """

        def wrapper(self, *args, **kwargs):
            if self.ses is None:
                server_id = kwargs.get("server_id")
                if server_id is None:
                    raise ValueError(
                        "!!!server_id must be passed as a keyword argument!!!"
                    )

                from initialization.db_processor_init import db_processor

                server = db_processor.get_server_by_id(server_id)
                if server is None:
                    raise ValueError(f"Сервер с ID {server_id} не найден в базе данных")

                self.ip = server.ip
                self.sub_port = 2096
                self.port_panel = 2053
                self.host = f"https://{self.ip}:{self.port_panel}"
                self.data = {"username": "admin", "password": server.password}

                try:
                    self.ses = requests.Session()
                    self.ses.verify = False
                    self.con = self._connect()
                except Exception as e:
                    self.ses = None
                    raise RuntimeError(f"Ошибка при установке соединения: {e}")

            return func(self, *args, **kwargs)

        return wrapper

    async def create_server_session(self) -> None:
        """
        Создает сессию для подключения к серверу с минимальным количеством пользователей для типа "vless".

        :return: `None`

        Алгоритм работы:
        1. Получает сервер с минимальным количеством пользователей для типа "vless" с использованием `db_processor`.
        2. Извлекает параметры подключения (IP, порты, данные для аутентификации).
        3. Инициализирует объект сессии с помощью `requests.Session`.
        4. Отключает проверку сертификатов с помощью `self.ses.verify = False`.
        5. Устанавливает соединение с сервером через метод `_connect()`.
        6. Сохраняет ID сервера в атрибуте `self.server_id`.
        """
        from initialization.db_processor_init import db_processor

        server = await db_processor.get_server_with_min_users("vless")

        self.ip = server.ip
        self.sub_port = 2096
        self.port_panel = 2053
        self.host = f"https://{self.ip}:{self.port_panel}"
        self.data = {"username": "admin", "password": server.password}
        self.ses = requests.Session()
        self.ses.verify = False
        self.con = self._connect()
        self.server_id = server.id

    def _connect(self) -> bool:
        """
        Авторизация в панели.
        """
        try:
            resp = self.ses.post(f"{self.host}/login", data=self.data).json()
            if resp.get("success") is True:
                logger.debug(f"✅Подключение к панели 3x-ui {self.ip} прошло успешно!")
                return True
            else:
                logger.warning(
                    f'🛑Подключение к панели 3x-ui {self.ip} не произошло, ошибка: {resp.get("msg")}'
                )
                return False
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при подключении к {self.host}: {e}")
            return False
        except ValueError as e:
            logger.error(f"Ошибка при декодировании JSON-ответа от {self.host}: {e}")
            return False

    def _check_connect(self) -> bool:
        """
        Проверяем, есть ли уже inbound (подключение), или нужно создавать новое.
        """
        if not self.con:
            return False

        try:
            resource = self.ses.post(
                f"{self.host}/panel/inbound/list/", data=self.data
            ).json()
            if not resource.get("success"):
                logger.warning(
                    f'🛑Ошибка при проверке подключения: {resource.get("msg")}'
                )
                return False
            # Если inbound'ы есть, считаем, что подключение уже настроено
            if resource.get("obj") and len(resource["obj"]) > 0:
                logger.debug(f"Подключение уже есть")
                return True

            logger.warning(f"⚠️Подключение (inbound) не найдено")
            return False
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при _check_connect: {e}")
            return False

    def _add_new_connect(self) -> tuple[bool, str]:
        """
        Добавляет новый inbound (подключение).
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Добавляем новое подключение на сервере {self.ip}...")

        # Шаг 1: Получаем ключи (privateKey/publicKey)
        cert_ok, cert_obj_or_msg = self._get_new_x25519_cert()
        if not cert_ok:
            logger.warning(f"Не удалось получить X25519-сертификат: {cert_obj_or_msg}")
            return False, cert_obj_or_msg

        private_key = cert_obj_or_msg["privateKey"]
        public_key = cert_obj_or_msg["publicKey"]

        # Шаг 2: Собираем JSON для inbound/add
        header = {"Accept": "application/json"}
        data = {
            "up": 0,
            "down": 0,
            "total": 0,
            "remark": NAME_VPN_CONFIG,  # Название inbound
            "enable": True,
            "expiryTime": 0,
            "listen": "",
            "port": 46408,
            "protocol": "vless",
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": "test1",
                            "flow": "xtls-rprx-vision",
                            "email": "test1",
                            "limitIp": 0,
                            "totalGB": 0,
                            "expiryTime": 0,
                            "enable": True,
                            "tgId": "",
                            "subId": "yap2ddklr1imbhfq",
                        }
                    ],
                    "decryption": "none",
                    "fallbacks": [],
                }
            ),
            "streamSettings": json.dumps(
                {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "xver": 0,
                        "dest": "google.com:443",
                        "serverNames": ["google.com", "www.google.com"],
                        "privateKey": private_key,
                        "minClient": "",
                        "maxClient": "",
                        "maxTimediff": 0,
                        "shortIds": [
                            "03b090ff397c50b9",
                            "7ea960",
                            "765c89c0ab102d",
                            "b5b79d7c18f0",
                            "1f52d659ec",
                            "4da9671e",
                            "45a0",
                            "d3",
                        ],  # Короткий ID
                        "settings": {
                            "publicKey": public_key,
                            "fingerprint": "chrome",
                            "serverName": "",
                            "spiderX": "/",
                        },
                    },
                    "tcpSettings": {
                        "acceptProxyProtocol": False,
                        "header": {"type": "none"},
                    },
                }
            ),
            "sniffing": json.dumps({"enabled": False, "destOverride": []}),
        }

        # Шаг 3: Добавляем inbound
        try:
            response = self.ses.post(
                f"{self.host}/panel/inbound/add", headers=header, json=data
            ).json()
            if response.get("success"):
                logger.debug(f"Добавили новое подключение на сервере {self.ip}")
                return True, response["obj"]
            else:
                msg = response.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при добавлении нового подключения: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении inbound: {e}")
            return False, str(e)

    def _get_new_x25519_cert(self) -> tuple[bool, dict]:
        """
        Запрашивает у панели новую пару ключей (privateKey / publicKey).
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        try:
            response = self.ses.post(
                f"{self.host}/server/getNewX25519Cert", data=self.data
            ).json()
            if response.get("success"):
                return True, response["obj"]
            else:
                return False, response.get("msg", "Неизвестная ошибка")
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при запросе X25519Cert: {e}")
            return False, str(e)

    def _get_link(self, key_id: str, key_name: str) -> str | bool:
        """
        Генерация ссылки для клиента (vless://...) для подключения к серверу.

        :param key_id: Уникальный идентификатор ключа для клиента.
        :param key_name: Имя ключа для клиента, которое будет отображаться в ссылке.

        :return: Сгенерированная ссылка для клиента, если успешно, иначе `False`.

        Алгоритм работы:
        1. Проверяется наличие активного соединения.
        2. Выполняется POST-запрос к панели управления для получения списка inbound соединений.
        3. Проверяется наличие успешного ответа и данных о первом inbound соединении.
        4. Извлекаются параметры настройки потока (streamSettings), включая публичный ключ.
        5. Формируется ссылка для клиента с использованием полученных данных.
        6. В случае ошибок в процессе генерируется лог с подробным описанием.
        """

        if not self.con:
            return False

        try:
            resource = self.ses.post(
                f"{self.host}/panel/inbound/list/", data=self.data
            ).json()
            if not resource.get("success"):
                return False

            # Первый inbound
            inbound_obj = resource["obj"][0] if resource["obj"] else None
            if not inbound_obj:
                return False

            # Достаём "streamSettings" и парсим как JSON
            stream_settings_str = inbound_obj.get("streamSettings")
            if not stream_settings_str:
                return False

            stream_settings = json.loads(stream_settings_str)
            port = inbound_obj.get("port", 443)

            reality = stream_settings.get("realitySettings", {})
            sett = reality.get("settings", {})
            public_key = sett.get("publicKey", "")
            sni = "www.google.com"
            flow = stream_settings.get("flow", "xtls-rprx-vision")

            # Формируем ссылку
            prev_text = ""
            bottom_text = f"#{key_name}"
            sid = "03b090ff397c50b9"

            res = (
                f"{prev_text}vless://{key_id}@{self.ip}:{port}/?type=tcp&security=reality&pbk={public_key}"
                f"&fp=chrome&sni=www.google.com&sid={sid}&spx=%2F&flow={flow}{bottom_text}"
            )
            return res
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Ошибка при генерации ссылки: {e}")
            return False

    async def create_vpn_key(
        self, expire_time: int = 0, sni: str = "dl.google.com", port: int = 46408
    ) -> tuple[VlessKey, int]:
        """
        Создает новый VPN-ключ VLESS на удаленном сервере.

        :param expire_time: Время жизни ключа в секундах (0 — бессрочный).
        :param sni: Server Name Indication (SNI) для шифрования.
        :param port: Порт для подключения.

        :return: Созданный VLESS-ключ и ID сервера, либо ошибка.

        :raises requests.RequestException: Ошибка сети при отправке запроса.

        Алгоритм работы:
        1. Устанавливает соединение с сервером (`create_server_session`).
        2. Генерирует уникальный ID для нового клиента.
        3. Отправляет POST-запрос на сервер для добавления нового ключа.
        4. Извлекает публичный ключ и настройки потока (stream settings) из ответа сервера.
        5. Формирует ссылку доступа (`access_url`) с параметрами подключения.
        6. Возвращает объект `VlessKey` и ID сервера при успешном создании, либо ошибку.
        """

        await self.create_server_session()
        if not self.con:
            return False, "Нет подключения к серверу"

        header = {"Accept": "application/json"}

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)

        key_name = generate_slug(2).replace("-", " ")
        data_limit = 200 * 1024**3  # лимит в байтах
        unique_id = str(uuid.uuid4())
        data = {
            "id": 1,
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": unique_id,  # должен быть уникальным, чтобы удалять ключи
                            "alterId": 0,
                            "email": unique_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": data_limit,
                            "expiryTime": expire_time,
                            "enable": True,
                            "tgId": "",
                            "subId": unique_id,
                            "flow": "xtls-rprx-vision",
                            "comment": key_name,  # имя ключа, которое видит пользователь
                            "up": 0,
                            "down": 0,
                        }
                    ]
                }
            ),
        }

        command = "/panel/inbound/addClient"

        resource = self.ses.post(
            f"{self.host}/panel/inbound/list/", data=self.data
        ).json()

        inbound_obj = resource["obj"][0] if resource["obj"] else None

        stream_settings_str = inbound_obj.get("streamSettings")
        stream_settings = json.loads(stream_settings_str)

        reality = stream_settings.get("realitySettings", {})
        sett = reality.get("settings", {})
        public_key = sett.get("publicKey", "")
        flow = stream_settings.get("flow", "xtls-rprx-vision")

        # Формируем ссылку
        prev_text = ""
        bottom_text = f"#{key_name}"
        sid = "03b090ff397c50b9"

        access_url = (
            f"{prev_text}vless://{unique_id}@{self.ip}:{port}/?type=tcp&security=reality&pbk={public_key}"
            f"&fp=chrome&sni=www.google.com&sid={sid}&spx=%2F&flow={flow}{bottom_text}"
        )

        try:
            resource = self.ses.post(
                f"{self.host}{command}", headers=header, json=data
            ).json()
            if resource.get("success"):
                logger.debug(f"Добавили ключ {unique_id} на сервере {self.ip}")
                return (
                    VlessKey(
                        key_id=unique_id,
                        email=unique_id,
                        name=key_name,
                        access_url=access_url,
                        used_bytes=0,
                        data_limit=data_limit,
                    ),
                    self.server_id,
                )
            else:
                msg = resource.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при добавлении ключа {unique_id}: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
            return False, str(e)

    @create_server_session_by_id
    async def rename_key(self, key_id: str, server_id: int, new_key_name: str) -> bool:
        """
        Переименовывает существующий VPN-ключ VLESS на удаленном сервере.

        :param key_id: Уникальный идентификатор ключа.
        :param server_id: Идентификатор сервера, на котором находится ключ.
        :param new_key_name: Новое имя для VPN-ключа.

        :return: True, если ключ успешно переименован, иначе False.

        :raises requests.RequestException: Ошибка сети при отправке запроса.

        Алгоритм работы:
        1. Проверяет наличие активного подключения (`self.con`).
        2. Логирует процесс обновления ключа.
        3. Формирует тело запроса с новыми параметрами ключа.
        4. Отправляет POST-запрос на сервер для обновления ключа.
        5. Анализирует ответ сервера и возвращает результат.
        6. В случае ошибки сети логирует и возвращает `False`.
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Обновляем ключ {key_id} на сервере {self.ip}...")

        header = {"Accept": "application/json"}

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)

        data = {
            "id": 1,
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": key_id,  # должен быть уникальным, чтобы удалять нормально
                            "alterId": 0,  # тут будет имя ключа
                            "email": key_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": 200 * 1024**3,
                            "expiryTime": 0,
                            "enable": "true",
                            "tgId": "",
                            "subId": key_id,
                            "flow": "xtls-rprx-vision",
                            "comment": new_key_name,
                        }
                    ]
                }
            ),
        }

        command = f"/panel/inbound/updateClient/{key_id}"

        try:
            resource = self.ses.post(
                f"{self.host}{command}", headers=header, json=data
            ).json()
            if resource.get("success"):
                logger.debug(f"Обновили ключ {key_id} на сервере {self.ip}")
                return True
            else:
                msg = resource.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при обновлении ключа {key_id}: {msg}")
                return False

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
            return False, str(e)

    @create_server_session_by_id
    async def delete_key(self, key_id: int, server_id: int | None = None) -> bool:
        """
        Удаляет клиентский ключ по указанному ID на сервере с заданным server_id.

        :param key_id: Идентификатор ключа для удаления.
        :param server_id: Идентификатор сервера (необязательный параметр, если передан, используется для получения данных сервера).

        :return: `True`, если ключ был успешно удален, в противном случае `False` с сообщением об ошибке.

        Алгоритм работы:
        1. Проверяет, если нет подключения к серверу, возвращает ошибку.
        2. Отправляет запрос на удаление ключа по указанному `key_id` на сервере.
        3. Если запрос успешен, возвращает `True`.
        4. В случае ошибки или неудачи выводит предупреждение с сообщением.
        5. В случае ошибки сети возвращает `False` и логирует ошибку.
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Удаляем ключ c id{key_id} на сервере {self.ip}...")

        try:
            # /panel/inbound/<id>/delClient/<email>
            response = self.ses.post(
                f"{self.host}/panel/inbound/1/delClient/{key_id}", data=self.data
            ).json()
            if response.get("success"):
                logger.debug(f"Удалили ключ {key_id}")
                return True
            else:
                msg = response.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при удалении ключа {key_id}: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при удалении ключа: {e}")
            return False

    @create_server_session_by_id
    async def get_key_info(self, key_id: str, server_id: int = None) -> VlessKey:
        """
        Получает информацию о VPN-ключе VLESS с удаленного сервера.

        :param key_id: Уникальный идентификатор ключа.
        :param server_id: Идентификатор сервера (опционально).

        :return: Объект `VlessKey`, содержащий информацию о ключе, или `None`, если ключ не найден.

        :raises requests.RequestException: Ошибка сети при отправке запроса.
        :raises ValueError: Ошибка при декодировании JSON-ответа.

        Алгоритм работы:
        1. Проверяет наличие активного подключения (`self.con`).
        2. Выполняет POST-запрос для получения списка ключей.
        3. Проверяет успешность запроса, логирует возможные ошибки.
        4. Ищет указанный `key_id` среди полученных inbound'ов.
        5. Если ключ найден, формирует объект `VlessKey` и возвращает его.
        6. В случае ошибки сети или некорректного JSON-ответа логирует и возвращает `None`.
        """
        if not self.con:
            logger.warning(f"Нет подключения к серверу")
            return None

        try:
            response = self.ses.post(
                f"{self.host}/panel/inbound/list/", data=self.data
            ).json()
            if not response.get("success"):
                logger.warning(
                    f'🛑Ошибка при получении списка ключей: {response.get("msg")}'
                )
                return None

            # Ищем ключ в списке inbound'ов
            for inbound in response.get("obj", []):
                clients = json.loads(inbound.get("settings", "{}")).get("clients", [])

                for client in clients:
                    if client.get("id") == key_id:
                        print(json.dumps(client, indent=4))
                        return VlessKey(
                            key_id=client.get("id"),
                            name=client.get("comment", ""),
                            email=client.get("email", ""),
                            access_url=self._get_link(
                                client.get("id"), client.get("comment", "")
                            ),
                            used_bytes=client.get("up", 0) + client.get("down", 0),
                            data_limit=(
                                client.get("totalGB") if client.get("totalGB") else None
                            ),
                        )

            logger.warning(f"Ключ {key_id} не найден на сервере")
            return None

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при получении информации о ключе {key_id}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Ошибка при декодировании JSON-ответа: {e}")
            return None

    @create_server_session_by_id
    async def update_data_limit(
        self,
        key_id: str,
        new_limit_bytes: int,
        server_id: int = None,
        key_name: str = None,
    ) -> bool:
        """
        Обновляет лимит данных для указанного пользователя на сервере.

        :param key_id: ID ключа, для которого обновляется лимит.
        :param new_limit_bytes: Новый лимит данных в байтах.
        :param server_id: ID сервера, на котором обновляется лимит данных.

        :return: True, если обновление прошло успешно, иначе False.
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Обновляем лимит для ключа {key_id} на сервере {self.ip}...")

        header = {"Accept": "application/json"}

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)

        data = {
            "id": 1,
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": key_id,  # должен быть уникальным, чтобы удалять нормально
                            "alterId": 0,  # тут будет имя ключа
                            "email": key_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": new_limit_bytes,
                            "expiryTime": 0,
                            "enable": "true",
                            "tgId": "",
                            "subId": key_id,
                            "flow": "xtls-rprx-vision",
                            "comment": key_name,
                        }
                    ]
                }
            ),
        }

        command = f"/panel/inbound/updateClient/{key_id}"

        try:
            resource = self.ses.post(
                f"{self.host}{command}", headers=header, json=data
            ).json()
            if resource.get("success"):
                logger.debug(
                    f"Успешно обновили лимит для ключа {key_id} на сервере {self.ip}"
                )
                return True
            else:
                msg = resource.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при обновлении лимита ключа {key_id}: {msg}")
                return False

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
            return False, str(e)


    async def setup_server(self, server):
        """
        Автоматическая установка 3X-UI на сервер с предварительной настройкой Docker.

        :param server: Объект сервера с атрибутами `ip` и `password`.

        :return: `True` в случае успешной установки, иначе `False`.

        Алгоритм работы:
        1. Подключается к серверу через SSH.
        2. Останавливает и удаляет старый Docker.
        3. Очищает систему от остаточных файлов Docker.
        4. Устанавливает свежую версию Docker и Docker Compose.
        5. Загружает и выполняет скрипт установки `setup.sh`.
        6. Передает в `setup.sh` необходимые данные для автоматической настройки.
        7. Логирует все этапы выполнения, включая возможные ошибки.
        """

        # Команды для остановки Docker-сервисов
        stop_docker_cmds = [
            "sudo systemctl stop docker",
            "sudo systemctl stop docker.socket",
            "sudo systemctl stop containerd",
            "sudo systemctl stop containerd.socket",
            "sudo killall -9 dockerd containerd",
            "sudo apt remove --purge -y docker docker.io containerd runc",
            "sudo umount /var/run/docker/netns/default || true",
            "sudo rm -rf /var/lib/docker /etc/docker /var/run/docker*",
        ]

        # Команды для удаления старого Docker (включая удаление файла репозитория)
        remove_docker_cmds = [
            "sudo apt update",
            "sudo apt install -y ca-certificates curl gnupg lsb-release",
            "sudo install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null",
            "sudo chmod a+r /etc/apt/keyrings/docker.asc",
            # Удаляем старый файл репозитория (если существует)
            "sudo rm -f /etc/apt/sources.list.d/docker.list",
            "apt remove --purge -y docker docker-engine docker.io containerd runc",
            "rm -rf /var/lib/docker /etc/docker /var/run/docker*",
        ]

        # Команды для установки Docker и Docker Compose
        install_docker_cmds = [
            "sudo apt update",
            "apt install -y apt-transport-https ca-certificates curl software-properties-common",
            # Добавляем ключ и репозиторий Docker для Ubuntu 22.04 (jammy)
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null",
            "sudo chmod a+r /etc/apt/keyrings/docker.asc",
            # Удаляем старый репозиторий, если он есть, и создаём новый
            "sudo rm -f /etc/apt/sources.list.d/docker.list",
            "echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable' | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
            "sudo apt update",
            "apt install -y docker-ce docker-ce-cli containerd.io",
            'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
            "sudo chmod +x /usr/local/bin/docker-compose",
        ]
        vless_email = os.getenv("VLESS_EMAIL")
        vless_bot_token = os.getenv("VLESS_BOT_TOKEN")
        # Команда для скачивания setup.sh
        setup_script = "curl -sSL https://raw.githubusercontent.com/torikki-tou/team418/main/setup.sh -o setup.sh && chmod +x setup.sh"
        # Данные для автоматического ввода в setup.sh (каждая строка — ответ на соответствующий вопрос)
        setup_answers = (
            "\n".join(
                [
                    "admin",  # Логин
                    server.password,  # Пароль
                    "2053",  # Порт 3X-UI
                    server.ip,  # IP/домен
                    vless_email,  # Email
                    vless_bot_token,  # Telegram Bot Token
                    "lisa_helper",  # Telegram admin profile
                    "y",  # Автоматическое подтверждение перезаписи конфига
                ]
            )
            + "\n"
        )
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                async with asyncssh.connect(
                    host=server.ip,
                    username="root",
                    password=server.password,
                    known_hosts=None,
                ) as conn:
                    logger.info(f"Попытка {attempt + 1}/{max_attempts}...")
                    logger.info(f"🔗 Подключение к серверу {server.ip} установлено!")

                    # Остановка и удаление старого Docker
                    logger.info("🛑 Останавливаем старый Docker...")
                    for cmd in stop_docker_cmds:
                        logger.info(f"➡ Выполняем: {cmd}")
                        result = await conn.run(cmd, check=False)
                        if result.exit_status != 0:
                            logger.warning(
                                f"⚠ Ошибка при выполнении {cmd}: {result.stderr.strip()}"
                            )

                    logger.info("🗑️ Удаляем старый Docker (очистка)...")
                    for cmd in remove_docker_cmds:
                        logger.info(f"➡ Выполняем: {cmd}")
                        result = await conn.run(cmd, check=False)
                        if result.exit_status != 0:
                            logger.warning(
                                f"⚠ Ошибка при выполнении {cmd}: {result.stderr.strip()}"
                            )
                        else:
                            logger.info(result.stdout)

                    # Установка нового Docker
                    logger.info("⬇ Устанавливаем Docker и Docker Compose...")
                    for cmd in install_docker_cmds:
                        logger.info(f"➡ Выполняем: {cmd}")
                        result = await conn.run(cmd, check=False)
                        if result.exit_status != 0:
                            raise Exception(
                                f"Ошибка при установке Docker: {cmd}\n{result.stderr.strip()}"
                            )
                        logger.info(result.stdout)

                    # Скачивание setup.sh
                    logger.info("📥 Загружаем setup.sh...")
                    result = await conn.run(setup_script)
                    if result.exit_status != 0:
                        raise Exception(
                            f"Ошибка при загрузке setup.sh: {result.stderr.strip()}"
                        )
                    logger.info(result.stdout)

                    # Запуск setup.sh с автоматическим вводом ответов
                    logger.info("⚙️ Запускаем setup.sh с автоматическим вводом данных...")
                    result = await conn.run('bash -c "./setup.sh"', input=setup_answers)
                    if result.exit_status != 0:
                        raise Exception(
                            f"Ошибка при установке 3X-UI: {result.stderr.strip()}"
                        )
                    logger.info(result.stdout)

                    logger.info(
                        f"🎉 3X-UI успешно установлена! Теперь панель доступна на {server.ip}:2053"
                    )
                    return True

            except Exception as e:
                logger.info(f"❌ Ошибка при установке 3X-UI: {e}, попытка {attempt + 1}/{max_attempts}")
                if attempt < max_attempts - 1:
                    logger.info("Повторная попытка через 10 секунд...")
                    await asyncio.sleep(10)

        return False

    def get_server_info(self, server) -> dict:
        """
        Получение информации о сервере
        Возвращает данные в виде:
        {
            "name": "My Server",
            "serverId": "7fda0079-5317-4e5a-bb41-5a431dddae21",
            "metricsEnabled": true,
            "createdTimestampMs": 1536613192052,
            "version": "1.0.0",
            "accessKeyDataLimit": {"bytes": 8589934592},
            "portForNewAccessKeys": 1234,
            "hostnameForAccessKeys": "example.com"
        }
        """
        # Инициализация соединения с сервером панели
        self.ip = server.ip
        self.port_panel = 2053
        self.host = f"https://{self.ip}:{self.port_panel}"
        self.data = {"username": "admin", "password": server.password}
        self.ses = requests.Session()
        self.ses.verify = False

        if not self._connect():
            raise Exception("Не удалось подключиться к панели сервера")

        try:
            # Предполагается, что сервер предоставляет информацию по данному эндпоинту
            response = self.ses.post(f"{self.host}/server/info", data=self.data).json()
            if response.get("success"):
                return response.get("obj", {})
            else:
                raise Exception(
                    response.get("msg", "Ошибка получения информации о сервере")
                )
        except requests.RequestException as e:
            raise Exception(f"Ошибка сети: {e}")
