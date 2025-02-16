import requests
import json
import uuid

from logger.logging_config import setup_logger

logger = setup_logger()

# Константы (при необходимости отредактируйте)
NAME_VPN_CONFIG = "MyNewInbound"


class VlessPocessor:
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
            "port": 443,
            "protocol": "vless",
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": "test1",
                            "flow": "",
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
                        "dest": "vk.com:443",
                        "serverNames": ["vk.com", "www.vk.com"],
                        "privateKey": private_key,
                        "minClient": "",
                        "maxClient": "",
                        "maxTimediff": 0,
                        "shortIds": ["ffffffffff"],  # Короткий ID
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
            "sniffing": json.dumps(
                {"enabled": True, "destOverride": ["http", "tls", "quic", "fakedns"]}
            ),
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

    def _get_link(self, vpn_key, isIOS=False):
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

            print(stream_settings)

            reality = stream_settings.get("realitySettings", {})
            sett = reality.get("settings", {})
            public_key = sett.get("publicKey", "")

            # Формируем ссылку
            if isIOS:
                prev_text = f"http://{self.ip}/v?c=streisand://import/"
                bottom_text = f"&name={vpn_key}"
            else:
                prev_text = ""
                bottom_text = f"#{vpn_key}"

            # Здесь порт 443, fingerprint=chrome, sni=vk.com
            res = (
                f"{prev_text}vless://{vpn_key}@{self.ip}:443?type=tcp&security=reality"
                f"&fp=chrome&pbk={public_key}&sni=vk.com&sid=ffffffffff&spx=%2F{bottom_text}"
            )
            return res
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Ошибка при генерации ссылки: {e}")
            return False

    def add_or_update_key(self, vpn_key, isUpdate=False, isActiv=True, isIOS=False):
        """
        Добавляет (isUpdate=False) или обновляет (isUpdate=True) клиента с нужным id (vpn_key).
        Параметр isActiv=True/False включает или выключает клиента.
        """
        if not self.con:
            return False, "Нет подключения к серверу"

        if not isUpdate:
            logger.debug(f"Добавляем новый ключ {vpn_key} на сервере {self.ip}...")
        else:
            logger.debug(f"Обновляем ключ {vpn_key} на сервере {self.ip}...")

        header = {"Accept": "application/json"}
        isActiv_str = "true" if isActiv else "false"

        # Сформируем тело запроса
        # id=1 — это ID inbound'а (если у вас больше inbound'ов, возможно, нужно другое число)
        import json

        unique_id = str(uuid.uuid4())
        data = {
            "id": 1,
            "settings": json.dumps(
                {
                    "clients": [
                        {
                            "id": vpn_key,  # должен быть уникальным, чтобы удалять нормально
                            "alterId": "aboba",  # тут будет имя ключа
                            "email": unique_id,  # должен быть уникальным, чтобы добавлять ключи
                            "limitIp": 1,
                            "totalGB": 0,
                            "expiryTime": 0,
                            "enable": isActiv_str,
                            "tgId": "",
                            "subId": vpn_key,
                            "flow": "xtls-rprx-vision",
                        }
                    ]
                }
            ),
        }

        # Выбираем конечную точку
        if not isUpdate:
            command = "/panel/inbound/addClient"
        else:
            command = f"/panel/inbound/updateClient/{vpn_key}"

        try:
            resource = self.ses.post(
                f"{self.host}{command}", headers=header, json=data
            ).json()
            if resource.get("success"):
                if not isUpdate:
                    logger.debug(f"Добавили ключ {vpn_key} на сервере {self.ip}")
                else:
                    logger.debug(f"Обновили ключ {vpn_key} на сервере {self.ip}")
                return True, self._get_link(vpn_key, isIOS)
            else:
                msg = resource.get("msg", "Неизвестная ошибка")
                if not isUpdate:
                    logger.warning(f"🛑Ошибка при добавлении ключа {vpn_key}: {msg}")
                else:
                    logger.warning(f"🛑Ошибка при обновлении ключа {vpn_key}: {msg}")
                return False, msg
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при добавлении/обновлении ключа: {e}")
            return False, str(e)

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

    def activ_list(self):
        """
        Возвращает список активных ключей сервера в формате:
        [
            (vpn_key: str, traffic_bytes: int, url: str),
            ...
        ]
        """
        if not self.con:
            return []

        logger.debug(f"VLESS: Получаю список активных ключей сервера {self.ip}...")

        try:
            resource = self.ses.post(
                f"{self.host}/panel/inbound/list/", data=self.data
            ).json()
            if not resource.get("success"):
                logger.warning(f'🛑Ошибка при получении списка: {resource.get("msg")}')
                return []

            if not resource.get("obj"):
                logger.debug(f"Нет ни одного inbound")
                return []

            # Берём первый inbound
            data_inb = resource["obj"][0]

            # В массиве "clientStats" хранятся клиенты
            keys = []
            for client in data_inb.get("clientStats", []):
                # Если включен
                if str(client.get("enable", "false")).lower() == "true":
                    # Суммируем трафик
                    trafic = client.get("up", 0) + client.get("down", 0)
                    vpn_key = client.get("email", "")
                    url = self._get_link(vpn_key)  # Генерируем ссылку
                    keys.append((vpn_key, trafic, url))

            logger.debug(f"VLESS: Список активных ключей сервера {self.ip}: {keys}")
            return keys
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при получении списка ключей: {e}")
            return []
        except ValueError as e:
            logger.error(f"Ошибка парсинга JSON при получении списка ключей: {e}")
            return []
