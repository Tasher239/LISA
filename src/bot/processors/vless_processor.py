from dataclasses import dataclass
from coolname import generate_slug
import json
import requests
import uuid

from bot.processors.base_processor import BaseProcessor

from logger.logging_config import setup_logger

logger = setup_logger()

# Константы (при необходимости отредактируйте)
NAME_VPN_CONFIG = "MyNewInbound"


@dataclass
class VlessKey:
    """
    Describes a key in the VLESS server
    """

    key_id: str
    name: str
    email: str
    access_url: str
    used_bytes: int
    data_limit: int | None


class VlessProcessor(BaseProcessor):
    def __init__(self, ip, password):
        self.ip = ip
        # Порт сабскрипции может быть другим (2096). Если нужно, скорректируйте:
        self.sub_port = 2096

        # Порт панели 3x-ui (или вашей панели)
        self.port_panel = 2053

        self.host = f"http://{self.ip}:{self.port_panel}/mypanel"

        # Пользователь admin (или root), пароль из примера
        self.data = {"username": "admin", "password": password}

        self.ses = requests.Session()

        # Отключаем проверку сертификата (не рекомендуется для боевого окружения)
        self.ses.verify = False

        # Подключаемся к панели
        self.con = self._connect()

        # Если подключились, проверяем, есть ли уже нужный inbound;
        # Если нет - пытаемся добавить.
        if self.con:
            if not self._check_connect():
                self._add_new_connect()
        else:
            logger.warning(
                f"🛑Подключение к панели 3x-ui {self.ip} не произошло (авторизация неуспешна)."
            )

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
                prev_text = f"http://{self.ip}/v?c=streisand://import/"
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

    def create_vpn_key(self, expire_time=0, sni="www.google.com", port=46408) -> str:
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
                            # тут будет имя ключа, которое видит пользователь и которое надюсь можно менять
                            "email": unique_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": 0,
                            "expiryTime": expire_time,
                            "enable": True,
                            "tgId": "",
                            "subId": unique_id,
                            "flow": "xtls-rprx-vision",
                            "comment": key_name,
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
        sni = "www.google.com"
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
                return VlessKey(
                    key_id=unique_id,
                    email=unique_id,
                    name=key_name,
                    access_url=access_url,
                    used_bytes=0,
                    data_limit=None,
                )
            else:
                msg = resource.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при добавлении ключа {unique_id}: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
            return False, str(e)

    def rename_key(self, key_id: str, new_key_name: str) -> bool:
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

    def delete_key(self, vpn_key):
        """
        Удаляет клиента с именем vpn_key у inbound ID=1.
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        logger.debug(f"Удаляем ключ {vpn_key} на сервере {self.ip}...")

        try:
            # /panel/inbound/<id>/delClient/<email>
            response = self.ses.post(
                f"{self.host}/panel/inbound/1/delClient/{vpn_key}", data=self.data
            ).json()
            if response.get("success"):
                logger.debug(f"Удалили ключ {vpn_key}")
                return True, "Успешно удалено"
            else:
                msg = response.get("msg", "Неизвестная ошибка")
                logger.warning(f"🛑Ошибка при удалении ключа {vpn_key}: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при удалении ключа: {e}")
            return False, str(e)

    def get_key_info(self, key_id: str) -> VlessKey:
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
