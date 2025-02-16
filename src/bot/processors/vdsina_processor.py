import aiohttp
import certifi
import ssl
import os

from dotenv import load_dotenv

from logger.logging_config import setup_logger

logger = setup_logger()

load_dotenv()

token = os.getenv("VDSINA_TOKEN")


class VDSinaAPI:
    def __init__(self):
        self.token = token  # Можно сразу брать из .env, если есть
        self.email = None
        self.password = None
        self.base_url = "https://userapi.vdsina.com/v1"

    async def authenticate(self, email=None, password=None):
        """Получение токена для авторизации"""
        if email:
            self.email = email
        if password:
            self.password = password

        if not self.email or not self.password:
            raise Exception("Необходимо указать email и password для аутентификации.")

        url = f"{self.base_url}/auth"
        payload = {"email": self.email, "password": self.password}
        headers = {"Content-Type": "application/json"}
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                if response_data.get("status") == "ok":
                    self.token = response_data["data"]["token"]
                    logger.info(
                        f"Авторизация успешна. Получен токен: {self.token[:10]}..."
                    )
                else:
                    raise Exception(
                        "Ошибка авторизации: "
                        + response_data.get("status_msg", "Неизвестная ошибка")
                    )

    async def request(self, method, endpoint, data=None):
        """Универсальный метод для запросов к API VDSina"""
        if not self.token:
            # Можно либо вызвать authenticate, либо выдать ошибку
            raise Exception(
                "Нет авторизационного токена. Сначала вызовите authenticate()."
            )

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.token, "Content-Type": "application/json"}

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with session.post(url, json=data, headers=headers) as response:
                    return await response.json()
            elif method.upper() == "PUT":
                async with session.put(url, json=data, headers=headers) as response:
                    return await response.json()
            elif method.upper() == "DELETE":
                async with session.delete(url, json=data, headers=headers) as response:
                    return await response.json()
            else:
                raise ValueError(f"Неподдерживаемый метод запроса: {method}")

    async def get_datacenters(self):
        """Получение списка дата-центров"""
        return await self.request("GET", "/datacenter")

    async def get_server_plans(self, group_id=1):
        """Получение списка тарифов"""
        return await self.request("GET", f"/server-plan/{group_id}")

    async def get_templates(self):
        """Получение списка доступных ОС"""
        return await self.request("GET", "/template")

    async def deploy_server(
        self, datacenter_id, server_plan_id, template_id, name="MyServer"
    ):
        """Разворачивание нового сервера"""
        payload = {
            "datacenter": datacenter_id,
            "server-plan": server_plan_id,
            "template": template_id,
            "name": name,
            "ip4": 1,
        }
        return await self.request("POST", "/server", payload)

    async def get_server_status(self, server_id):
        """Получение информации о сервере"""
        return await self.request("GET", f"/server/{server_id}")

    async def create_new_server(
        self,
        datacenter_id,
        server_plan_id,
        template_id,
        ip4=1,
        email=None,
        password=None,
    ):
        # Если токена нет, пробуем авторизоваться
        if not self.token:
            await self.authenticate(email, password)
        # После успешной авторизации пробуем создать сервер
        return await self.deploy_server(datacenter_id, server_plan_id, template_id, ip4)

    async def get_servers(self):
        return await self.request("GET", "/server")

    async def get_server_statistics(self, server_id, from_date=None, to_date=None):
        if not from_date and to_date:
            endpoint = f"/server.stat/{server_id}?to={to_date}"
        elif from_date and not to_date:
            endpoint = f"/server.stat/{server_id}?from={from_date}"
        elif from_date and to_date:
            endpoint = f"/server.stat/{server_id}?from={from_date}&to={to_date}"
        else:
            endpoint = f"/server.stat/{server_id}"

        return await self.request("GET", endpoint)
