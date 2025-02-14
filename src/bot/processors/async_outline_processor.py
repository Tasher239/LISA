from outline_vpn.outline_vpn import OutlineKey
from coolname import generate_slug
import asyncio
import base64
import aiohttp
import asyncssh
import json
import re

from bot.processors.structs import OutlineKey
from bot.processors.base_processor import BaseProcessor
from logger.logging_config import setup_logger

logger = setup_logger()


class OutlineServerErrorException(Exception):
    pass


def get_aiohttp_fingerprint(ssl_assert_fingerprint: str) -> aiohttp.Fingerprint:
    return aiohttp.Fingerprint(
        base64.b16decode(ssl_assert_fingerprint.replace(":", ""), casefold=True)
    )


class OutlineProcessor(BaseProcessor):
    """
    An Outline VPN connection
    """

    def __init__(self):
        self.api_url = None
        self.cert_sha256 = None
        self.session: aiohttp.ClientSession | None = None
        self.server_id = None

    def create_server_session_by_id(func):
        async def wrapper(self, *args, **kwargs):
            if self.session is None:
                if kwargs.get("server_id") is None:
                    raise ValueError(
                        "!!!server_id must be passed as a keyword argument!!!"
                    )

                server_id = kwargs.get("server_id")
                from bot.initialization.db_processor_init import db_processor

                server = db_processor.get_server_by_id(server_id)
                self.api_url = server.api_url
                self.server_id = server_id
                connector = aiohttp.TCPConnector(
                    ssl=get_aiohttp_fingerprint(
                        ssl_assert_fingerprint=server.cert_sha256
                    )
                )
                session = aiohttp.ClientSession(connector=connector)
                self.session = session

            return await func(self, *args, **kwargs)

        return wrapper

    async def create_server_session(self) -> None:
        from bot.initialization.db_processor_init import db_processor

        server = await db_processor.get_server_with_min_users("outline")

        self.api_url = server.api_url
        self.server_id = server.id
        connector = aiohttp.TCPConnector(
            ssl=get_aiohttp_fingerprint(ssl_assert_fingerprint=server.cert_sha256)
        )
        session = aiohttp.ClientSession(connector=connector)
        self.session = session

    async def create_server_session_for_server(self, server) -> None:
        self.api_url = server.api_url
        self.server_id = server.id
        connector = aiohttp.TCPConnector(
            ssl=get_aiohttp_fingerprint(ssl_assert_fingerprint=server.cert_sha256)
        )
        session = aiohttp.ClientSession(connector=connector)
        self.session = session

    async def _get_metrics(self) -> dict:
        async with self.session.get(url=f"{self.api_url}/metrics/transfer") as resp:
            resp_json = await resp.json()
            if resp.status >= 400 or "bytesTransferredByUserId" not in resp_json:
                raise OutlineServerErrorException("Unable to get metrics")

            return resp_json

    async def _get_raw_keys(self) -> list[OutlineKey]:
        async with self.session.get(
            url=f"{self.api_url}/access-keys/",
        ) as resp:
            response_data = await resp.json()
            if resp.status != 200 or "accessKeys" not in response_data:
                raise OutlineServerErrorException("Unable to retrieve keys")

        return [
            OutlineKey.from_key_json(key_data)
            for key_data in response_data.get("accessKeys", [])
        ]

    async def create_vpn_key(self) -> tuple[OutlineKey, int]:
        """Create a new key"""
        await self.create_server_session()
        async with self.session.post(url=f"{self.api_url}/access-keys/") as resp:
            if resp.status != 201:
                raise OutlineServerErrorException("Unable to create key")
            key = await resp.json()
            tmp_key = OutlineKey.from_key_json(key)
            logger.info(tmp_key)

            key_name = generate_slug(2).replace("-", " ")
            data_limit = 200

            await self.rename_key(tmp_key.key_id, key_name)
            await self.add_data_limit(tmp_key.key_id, data_limit)

            key["name"] = key_name
            key["used_bytes"] = 0
            key["data_limit"] = 100

        outline_key = OutlineKey.from_key_json(key)
        return outline_key, self.server_id

    @create_server_session_by_id
    async def get_key_info(self, key_id: int, server_id=None) -> OutlineKey:
        """!!!!!!server_id нужно передавать как ключевой аргумент!!!!!!!!
        т.е. нельзя вызывать эту функцию как get_key_info(my_key_id, my_server_id)
        дожно быть  get_key_info(my_key_id, server_id=my_server_id)
        """
        async with self.session.get(url=f"{self.api_url}/access-keys/{key_id}") as resp:
            if resp.status != 200:
                raise OutlineServerErrorException("Unable to retrieve keys")
            client_data = OutlineKey.from_key_json(await resp.json())
        current_metrics = await self._get_metrics()

        client_data.used_bytes = current_metrics.get("bytesTransferredByUserId").get(
            client_data.key_id
        )
        return client_data

    async def delete_key(self, key_id: int) -> bool:
        """Delete a key"""
        async with self.session.delete(
            url=f"{self.api_url}/access-keys/{key_id}"
        ) as resp:
            return resp.status == 204

    @create_server_session_by_id
    async def rename_key(self, key_id, new_key_name, server_id=None) -> bool:
        """Rename a key"""
        async with self.session.put(
            url=f"{self.api_url}/access-keys/{key_id}/name", data={"name": new_key_name}
        ) as resp:
            return resp.status == 204

    async def _fulfill_keys_with_metrics(
        self, keys: list[OutlineKey]
    ) -> list[OutlineKey]:
        current_metrics = await self._get_metrics()

        for key in keys:
            key.used_bytes = current_metrics.get("bytesTransferredByUserId").get(
                key.key_id
            )
        return keys

    async def get_keys(self):
        """Get all keys in the outline server"""
        raw_keys = await self._get_raw_keys()

        result_keys = await self._fulfill_keys_with_metrics(keys=raw_keys)

        return result_keys

    async def add_data_limit(self, key_id: int, limit_bytes: int) -> bool:
        """Set data limit for a key (in bytes)"""
        data = {"limit": {"bytes": limit_bytes}}

        async with self.session.put(
            url=f"{self.api_url}/access-keys/{key_id}/data-limit", json=data
        ) as resp:
            return resp.status == 204

    async def delete_data_limit(self, key_id: int) -> bool:
        """Removes data limit for a key"""
        async with self.session.delete(
            url=f"{self.api_url}/access-keys/{key_id}/data-limit"
        ) as resp:
            return resp.status == 204

    async def get_transferred_data(self) -> dict:
        """Gets how much data all keys have used
        {
            "bytesTransferredByUserId": {
                "1":1008040941,
                "2":5958113497,
                "3":752221577
            }
        }"""
        async with self.session.get(url=f"{self.api_url}/metrics/transfer") as resp:
            resp_json = await resp.json()
            if resp.status >= 400 or "bytesTransferredByUserId" not in resp_json:
                raise OutlineServerErrorException("Unable to get metrics")
        return resp_json

    async def get_server_information(self) -> dict:
        """Get information about the server
        {
            "name":"My Server",
            "serverId":"7fda0079-5317-4e5a-bb41-5a431dddae21",
            "metricsEnabled":true,
            "createdTimestampMs":1536613192052,
            "version":"1.0.0",
            "accessKeyDataLimit":{"bytes":8589934592},
            "portForNewAccessKeys":1234,
            "hostnameForAccessKeys":"example.com"
        }
        """
        async with self.session.get(url=f"{self.api_url}/server") as resp:
            resp_json = await resp.json()
            if resp.status != 200:
                raise OutlineServerErrorException(
                    "Unable to get information about the server"
                )
        return resp_json

    async def set_server_name(self, name: str) -> bool:
        """Renames the server"""
        data = {"name": name}
        async with self.session.put(url=f"{self.api_url}/name", json=data) as resp:
            return resp.status == 204

    async def set_hostname(self, hostname: str) -> bool:
        """Changes the hostname for access keys.
        Must be a valid hostname or IP address."""
        data = {"hostname": hostname}
        async with self.session.put(
            url=f"{self.api_url}/server/hostname-for-access-keys", json=data
        ) as resp:
            return resp.status == 204

    async def get_metrics_status(self) -> bool:
        """Returns whether metrics is being shared"""
        async with self.session.get(url=f"{self.api_url}/metrics/enabled") as resp:
            resp_json = await resp.json()
            return resp_json.get("metricsEnabled")

    async def set_metrics_status(self, status: bool) -> bool:
        """Enables or disables sharing of metrics"""
        data = {"metricsEnabled": status}
        async with self.session.put(
            url=f"{self.api_url}/metrics/enabled", json=data
        ) as resp:
            return resp.status == 204

    async def set_port_new_for_access_keys(self, port: int) -> bool:
        """Changes the default port for newly created access keys.
        This can be a port already used for access keys."""
        data = {"port": port}
        async with self.session.put(
            url=f"{self.api_url}/server/port-for-new-access-keys", json=data
        ) as resp:
            if resp.status == 400:
                raise OutlineServerErrorException(
                    "The requested port wasn't an integer from 1 through 65535, or the request had no port parameter."
                )
            elif resp.status == 409:
                raise OutlineServerErrorException(
                    "The requested port was already in use by another service."
                )
            return resp.status == 204

    async def set_data_limit_for_all_keys(self, limit_bytes: int) -> bool:
        """Sets a data transfer limit for all access keys."""
        data = {"limit": {"bytes": limit_bytes}}
        async with self.session.put(
            url=f"{self.api_url}/server/access-key-data-limit", json=data
        ) as resp:
            return resp.status == 204

    async def delete_data_limit_for_all_keys(self) -> bool:
        """Removes the access key data limit, lifting data transfer restrictions on all access keys."""
        async with self.session.delete(
            url=f"{self.api_url}/server/access-key-data-limit"
        ) as resp:
            return resp.status == 204

    async def _close(self):
        await self.session.close()

    def __del__(self):
        if self.session is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._close())
            return
        loop.create_task(self._close())

    async def close(self):
        if self.session:
            await self.session.close()

    def extract_outline_config(output: str) -> dict | None:
        match = re.search(r"(\{[^}]+\})", output)
        if match:
            json_str = match.group(1)
            try:
                config = json.loads(json_str)
                if "apiUrl" in config and "certSha256" in config:
                    return config
            except json.JSONDecodeError:
                pass
        return None

    async def setup_server_outline(self, server):
        await self.create_server_session_for_server(server)
        install_cmd = [
            "sudo apt update && sudo apt install -y docker.io",
            'sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/Jigsaw-Code/outline-server/master/src/server_manager/install_scripts/install_server.sh)',
        ]
        try:
            async with asyncssh.connect(
                host=server.ip,
                username="root",
                password=server.password,
                known_hosts=None,
            ) as conn:
                for cmd in install_cmd:
                    result = await asyncio.wait_for(conn.run(cmd, input="y\n"), timeout=300)
                    print(result.stdout)
                    if result.exit_status != 0:
                        raise Exception(f"Error executing command: {cmd}")
                config = self.extract_outline_config(result.stdout)
                if config is None:
                    raise Exception("Error while extracting config")
                server.api_url = config["apiUrl"]
                server.cert_sha256 = config["certSha256"]
                server.save()
        except Exception as e:
            logger.error(f"Error while setting up Outline server: {e}")
            return False


