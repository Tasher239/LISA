from abc import ABC, abstractmethod

from bot.processors.structs import OutlineKey, VlessKey


class BaseProcessor(ABC):
    @abstractmethod
    def create_server_session(self):
        pass

    @abstractmethod
    def create_vpn_key(self) -> tuple[OutlineKey | VlessKey, int]:
        """Создает ключ на сервере и возвращает строку ключа"""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Удаляет ключ с сервера и возвращает строку ключа"""
        pass

    @abstractmethod
    def rename_key(self, key_id: str, server_id: str, new_key_name: str) -> bool:
        pass

    @abstractmethod
    def get_key_info(self, key_id: str, server_id: int = None) -> OutlineKey | VlessKey:
        pass
