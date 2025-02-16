from coolname import generate_slug
from dotenv import load_dotenv
import requests
import asyncssh
import urllib3
import json
import uuid
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bot.processors.base_processor import BaseProcessor
from bot.processors.structs import VlessKey


from logger.logging_config import setup_logger

logger = setup_logger()

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

    def create_server_session_by_id(func):
        def wrapper(self, *args, **kwargs):
            if self.ses is None:
                if kwargs.get("server_id") is None:
                    raise ValueError(
                        "!!!server_id must be passed as a keyword argument!!!"
                    )
                from bot.initialization.db_processor_init import db_processor

                server_id = kwargs.get("server_id")
                server = db_processor.get_server_by_id(server_id)
                self.ip = server.ip
                self.sub_port = 2096
                self.port_panel = 2053
                self.host = f"http://{self.ip}:{self.port_panel}"
                self.data = {"username": "admin", "password": server.password}
                self.ses = requests.Session()
                self.ses.verify = False
                self.con = self._connect()
            return func(self, *args, **kwargs)

        return wrapper

    async def create_server_session(self):
        from bot.initialization.db_processor_init import db_processor

        server = await db_processor.get_server_with_min_users("vless")

        self.ip = server.ip
        self.sub_port = 2096
        self.port_panel = 2053
        self.host = f"http://{self.ip}:{self.port_panel}"
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

    def _get_link(self, key_id, key_name, isIOS=False):
        """
        Генерация ссылки для клиента (vless://...).
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

            if isIOS:
                prev_text = f"https://{self.ip}/v?c=streisand://import/"
                bottom_text = f"&name={key_id}"
            else:
                prev_text = ""
                bottom_text = f"#{key_name}"
            sid = "03b090ff397c50b9"
            # Здесь порт 443, fingerprint=chrome, sni=vk.com

            res = (
                f"{prev_text}vless://{key_id}@{self.ip}:{port}/?type=tcp&security=reality&pbk={public_key}"
                f"&fp=chrome&sni=www.google.com&sid={sid}&spx=%2F&flow={flow}{bottom_text}"
            )
            return res
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Ошибка при генерации ссылки: {e}")
            return False

    async def create_vpn_key(
        self, expire_time=0, sni="dl.google.com", port=46408
    ) -> tuple[VlessKey, int]:
        await self.create_server_session()
        if not self.con:
            return False, "Нет подключения к серверу"

        header = {"Accept": "application/json"}

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)
        import json

        key_name = generate_slug(2).replace("-", " ")

        unique_id = str(uuid.uuid4())
        data = {
            "id": 1,
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": unique_id,  # должен быть уникальным, чтобы удалять нормально
                            "alterId": 0,
                            "email": unique_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": 0,
                            "expiryTime": expire_time,
                            "enable": True,
                            "tgId": "",
                            "subId": unique_id,
                            "flow": "xtls-rprx-vision",
                            "comment": key_name,  # имя ключа, которое видит пользователь
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
        sni = "dl.google.com"
        flow = stream_settings.get("flow", "xtls-rprx-vision")
        # Формируем ссылку

        prev_text = ""
        bottom_text = f"#{key_name}"
        sid = "03b090ff397c50b9"
        # Здесь порт 443, fingerprint=chrome, sni=vk.com

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
                        data_limit=None,
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

    async def rename_key(self, key_id: str, server_id, new_key_name: str) -> bool:
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Обновляем ключ {key_id} на сервере {self.ip}...")

        header = {"Accept": "application/json"}

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)
        import json

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
                            "totalGB": 0,
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

    # def add_or_update_key(self, vpn_key, is_update=False, is_activ=True):
    #     """
    #     Добавляет (isUpdate=False) или обновляет (isUpdate=True) клиента с нужным id (vpn_key).
    #     Параметр isActiv=True/False включает или выключает клиента.
    #     """
    #     if not self.con:
    #         return False, "Нет подключения к серверу"
    #
    #     if not is_update:
    #         logger.debug(f"Добавляем новый ключ {vpn_key} на сервере {self.ip}...")
    #     else:
    #         logger.debug(f"Обновляем ключ {vpn_key} на сервере {self.ip}...")
    #
    #     header = {"Accept": "application/json"}
    #
    #     if is_activ:
    #         is_activ_str = "true"
    #     else:
    #         is_activ_str = "false"
    #
    #     # Сформируем тело запроса
    #     # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)
    #     import json
    #
    #     unique_id = str(uuid.uuid4())
    #     data = {
    #         "id": 1,
    #         "settings": json.dumps(
    #             {
    #                 "clients": [
    #                     {
    #                         "id": vpn_key,  # должен быть уникальным, чтобы удалять нормально
    #                         "alterId": 0,  # тут будет имя ключа
    #                         "email": unique_id,  # должен быть уникальным, чтобы добавлять ключи
    #                         "limitIp": 1,
    #                         "totalGB": 0,
    #                         "expiryTime": 0,
    #                         "enable": is_activ_str,
    #                         "tgId": "",
    #                         "subId": vpn_key,
    #                         "flow": "xtls-rprx-vision",
    #                     }
    #                 ]
    #             }
    #         ),
    #     }
    #
    #     # Выбираем конечную точку
    #     if not is_update:
    #         command = "/panel/inbound/addClient"
    #     else:
    #         command = f"/panel/inbound/updateClient/{vpn_key}"
    #
    #     try:
    #         resource = self.ses.post(
    #             f"{self.host}{command}", headers=header, json=data
    #         ).json()
    #         if resource.get("success"):
    #             if not is_update:
    #                 logger.debug(f"Добавили ключ {vpn_key} на сервере {self.ip}")
    #             else:
    #                 logger.debug(f"Обновили ключ {vpn_key} на сервере {self.ip}")
    #             return True, self._get_link(vpn_key, isIOS)
    #         else:
    #             msg = resource.get("msg", "Неизвестная ошибка")
    #             if not is_update:
    #                 logger.warning(f"🛑Ошибка при добавлении ключа {vpn_key}: {msg}")
    #             else:
    #                 logger.warning(f"🛑Ошибка при обновлении ключа {vpn_key}: {msg}")
    #             return False, msg
    #     except requests.RequestException as e:
    #         logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
    #         return False, str(e)

    @create_server_session_by_id
    async def delete_key(self, key_id, server_id=None) -> bool:
        """
        Удаляет клиента с именем vpn_key у inbound ID=1.
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
        Выполняет GET-запрос на сервер, получает информацию о ключе key_id и
        возвращает объект VlessKey.
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
                        return VlessKey(
                            key_id=client.get("id"),
                            name=client.get("comment", ""),
                            email=client.get("email", ""),
                            access_url=self._get_link(
                                client.get("id"), client.get("comment", "")
                            ),
                            used_bytes=client.get("up", 0) + client.get("down", 0),
                            data_limit=(
                                client.get("totalGB") * 1024 * 1024 * 1024
                                if client.get("totalGB")
                                else None
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

    async def setup_server_vless(self, server):
        """Автоматическая установка 3X-UI с вводом данных"""

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

        # Команда для скачивания setup.sh
        setup_script = "curl -sSL https://raw.githubusercontent.com/torikki-tou/team418/main/setup.sh -o setup.sh && chmod +x setup.sh"
        vless_password = os.getenv("VLESS_PASSWORD")
        vless_email = os.getenv("VLESS_EMAIL")
        vless_bot_token = os.getenv("VLESS_BOT_TOKEN")
        # Данные для автоматического ввода в setup.sh (каждая строка — ответ на соответствующий вопрос)
        setup_answers = (
            "\n".join(
                [
                    "admin",  # Логин
                    vless_password,  # Пароль
                    "2052",  # Порт 3X-UI
                    server.ip,  # IP/домен
                    vless_email,  # Email
                    vless_bot_token,  # Telegram Bot Token
                    "lisa_helper",  # Telegram admin profile
                    "y",  # Автоматическое подтверждение перезаписи конфига
                ]
            )
            + "\n"
        )

        try:
            async with asyncssh.connect(
                host=server.ip,
                username="root",
                password=server.password,
                known_hosts=None,
            ) as conn:
                logger.info(f"🔗 Подключение к серверу {server['ip']} установлено!")

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

                logger.success(
                    f"🎉 3X-UI успешно установлена! Теперь панель доступна на {server['ip']}:2052"
                )

        except Exception as e:
            logger.error(f"❌ Ошибка при настройке сервера {server['ip']}: {e}")
            return False

        return True

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
        self.port_panel = 2052
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
