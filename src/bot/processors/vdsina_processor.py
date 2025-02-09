import aiohttp
import asyncio


class VDSinaAPI:
    def __init__(self):
        self.token = None
        self.email = None
        self.password = None
        self.base_url = "https://userapi.vdsina.ru/v1"

    async def authenticate(self, email, password):
        """Получение токена для авторизации"""
        url = f"{self.base_url}/auth"
        payload = {"email": self.email, "password": self.password}
        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                if response_data.get("status") == "ok":
                    self.token = response_data["data"]["token"]
                else:
                    raise Exception(
                        "Ошибка авторизации: "
                        + response_data.get("status_msg", "Неизвестная ошибка")
                    )

    async def request(self, method, endpoint, data=None):
        """Универсальный метод для запросов к API"""
        if not self.token:
            await self.authenticate()

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, json=data, headers=headers
            ) as response:
                return await response.json()

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
            "ip4": 1,  # Подключение IPv4
        }
        return await self.request("POST", "/server", payload)

    async def get_server_status(self, server_id):
        """Получение информации о сервере"""
        return await self.request("GET", f"/server/{server_id}")

    async def create_new_server(self):
        pass
