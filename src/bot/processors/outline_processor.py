from outline_vpn.outline_vpn import OutlineKey
from bot.processors.base_processor import BaseProcessor

class OutlineProcessor(BaseProcessor):
    def __init__(self, client):
        self.client = client

    @staticmethod
    def gb_to_bytes(gb: float) -> int:
        bytes_in_gb = 1024**3  # 1 ГБ = 1024^3 байт
        return int(gb * bytes_in_gb)

    def get_keys(self) -> list[OutlineKey]:
        return self.client.get_keys()

    def get_key_info(self, key_id: str) -> str:
        return self.client.get_key(key_id)

    def _create_new_key(
        self, key_id: str = None, name: str = None, data_limit_gb: float = None
    ) -> str:
        """Создает новый ключ и возвращает строку информации о нем"""
        return self.client.create_key(
            key_id=key_id, name=name, data_limit=self.gb_to_bytes(data_limit_gb)
        )

    def rename_key(self, key_id: str, new_key_name: str) -> bool:
        """Переименовывает ключ и возвращает статус операции"""
        return self.client.rename_key(key_id, new_key_name)

    def upd_limit(self, key_id: str, data_limit_gb: float) -> bool:
        """Обновляет лимит трафика и возвращает статус операции"""
        return self.client.add_data_limit(key_id, self.gb_to_bytes(data_limit_gb))

    def delete_limit(self, key_id: str) -> bool:
        """Удаляет лимит трафика и возвращает статус операции"""
        return self.client.delete_data_limit(key_id)

    def delete_key(self, key_id: str) -> bool:
        """Удаляет ключ и возвращает статус операции"""
        return self.client.delete_key(key_id)

    def get_service_info(self) -> dict:
        """Получение информации о сервере
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
        return self.client.get_server_information()

    def create_vpn_key(self) -> str:
        """Создает новый VPN-ключ."""
        keys_lst = self.get_keys()
        max_id = max([int(key.key_id) for key in keys_lst])
        return self._create_new_key(
            key_id=max_id + 1, name=f"VPN Key{len(keys_lst) + 1}", data_limit_gb=1
        )
