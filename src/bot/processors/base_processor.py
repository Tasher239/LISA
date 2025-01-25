from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    @abstractmethod
    def create_vpn_key(self) -> str:
        """Создает ключ на сервере и возвращает строку ключа"""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Удаляет ключ с сервера и возвращает строку ключа"""
        pass

    @abstractmethod
    def rename_key(self, key_id: str, new_key_name: str) -> bool:
        pass

    @abstractmethod
    def get_key_info(self, key_id: str) -> str:
        pass
