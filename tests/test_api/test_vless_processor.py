import os
import pytest
from unittest import mock
import aiohttp

from api_processors.key_models import VlessKey
from api_processors.vless_processor import VlessProcessor
from database.models import Server
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def mock_vless_server():
    """Mock-сервер"""
    id = 1
    ip = os.getenv("VLESS_IP")
    password = os.getenv("VLESS_PASSWORD")
    protocol_type = "VLESS"
    return Server(id=id, ip=ip, password=password, protocol_type=protocol_type)


@pytest.fixture
def mock_processor(mock_vless_server):
    """Фикстура для процессора с патчем."""
    with mock.patch(
        "database.db_processor.DbProcessor.get_server_with_min_users",
        return_value=mock_vless_server,
    ):
        processor = VlessProcessor(os.getenv("VLESS_IP"), os.getenv("VLESS_PASSWORD"))
        yield processor


@pytest.fixture
@pytest.mark.asyncio
async def mock_vpn_key(mock_processor):
    """Фикстура для создания и автоматического удаления VPN-ключа."""
    key, server_id = await mock_processor.create_vpn_key()
    try:
        yield key, server_id
    finally:
        await mock_processor.delete_key(key.key_id, server_id=server_id)


@pytest.mark.asyncio
async def test_create_server_session(mock_processor):
    """Тестирование создания соединения с сервером
    создаем объект Server с паролем и логином из env
    запускаем функцию с сервером
    проверяем что сессия создалась
    """
    await mock_processor.create_server_session()
    assert mock_processor.ip == os.getenv("VLESS_IP")
    assert mock_processor.server_id == 1


@pytest.mark.asyncio
async def test_create_vpn_key(mock_processor, mock_vpn_key):
    """Тестирование создания ключа для обычного пользователя и админа"""
    key, server_id = await anext(mock_vpn_key)
    assert key is not None
    assert key.data_limit == 200 * 1024**3


@pytest.mark.asyncio
async def test_delete_key(mock_processor, mock_vpn_key):
    """Тестирование возможности удалить ключ"""
    key, server_id = await anext(mock_vpn_key)
    delete_status = await mock_processor.delete_key(key.key_id)
    assert delete_status is True


@pytest.mark.asyncio
async def test_valid_get_key_info(mock_processor, mock_vpn_key):
    """Тестирование получение информации о существующих ключах"""
    key, server_id = await anext(mock_vpn_key)
    key_info = await mock_processor.get_key_info(key.key_id, server_id=server_id)
    assert isinstance(key_info, VlessKey)
    assert key_info.key_id == key.key_id
    assert key_info.name == key.name
    assert key_info.data_limit == key.data_limit


@pytest.mark.asyncio
async def test_invalid_get_key_info_(mock_processor):
    """Тестирование получение информации о несуществующих ключах"""
    with pytest.raises(
        ValueError, match="!!!server_id must be passed as a keyword argument!!!"
    ):
        await mock_processor.get_key_info("invalid_key_id")
        await mock_processor.get_key_info("invalid_key_id", "not_keyword_server_id")


@pytest.mark.asyncio
async def test_rename_key(mock_processor, mock_vpn_key):
    """Тестирование переименования ключа"""
    key, server_id = await anext(mock_vpn_key)
    new_key_name = "new_key_name"
    rename_status = await mock_processor.rename_key(key.key_id, server_id, new_key_name)
    assert rename_status is True
    key_info = await mock_processor.get_key_info(key.key_id, server_id=server_id)
    assert key_info.name == new_key_name


@pytest.mark.asyncio
async def test_update_data_limit(mock_processor, mock_vpn_key):
    key, server_id = await anext(mock_vpn_key)
    assert key.data_limit == 200 * 1024**3
    new_data_limit = 300 * 10**9
    await mock_processor.update_data_limit(
        key.key_id, new_data_limit, server_id=server_id, key_name=key.name
    )
    key_info = await mock_processor.get_key_info(key.key_id, server_id=server_id)
    assert key_info.data_limit == new_data_limit
    assert key_info.name == key.name
