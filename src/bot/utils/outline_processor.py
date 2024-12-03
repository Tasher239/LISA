class OutlineProcessor:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def gb_to_bytes(gb: float) -> int:
        bytes_in_gb = 1024**3  # 1 ГБ = 1024^3 байт
        return int(gb * bytes_in_gb)

    def get_keys(self):
        return self.client.get_keys()

    def get_key_info(self, key_id: str) -> str:
        return self.client.get_key(key_id)

    def create_new_key(
        self, key_id: str = None, name: str = None, data_limit_gb: float = None
    ) -> str:
        """Создает новый ключ и возвращает строку инфы о нем"""
        return self.client.create_key(
            key_id=key_id, name=name, data_limit=self.gb_to_bytes(data_limit_gb)
        )

    def rename_key(self, key_id: str, new_key_name: str):
        """Переименовывает ключ и возвращает статус операции"""
        return self.client.rename_key(key_id, new_key_name)

    def upd_limit(self, key_id: str, data_limit_gb: float):
        """Обновляет лимит трафика и возвращает статус операции"""
        return self.client.add_data_limit(key_id, self.gb_to_bytes(data_limit_gb))

    def delete_limit(self, key_id: str):
        """Удаляет лимит трафика и возвращает статус операции"""
        return self.client.delete_data_limit(key_id)

    def delete_key(self, key_id: str):
        return self.client.delete_key(key_id)

    def get_service_info(self):
        return self.client.get_server_information()
