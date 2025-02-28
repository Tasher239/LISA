import os
import pytest
from unittest import mock
import aiohttp

from api_processors.key_models import OutlineKey
from api_processors.outline_processor import OutlineProcessor
from database.models import Server
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def mock_outline_server():
    """Mock-сервер"""
    id = 1
    api_url = os.getenv("OUTLINE_API_URL")
    cert_sha256 = os.getenv("OUTLINE_CERT_SHA")
    protocol_type = "Outline"
    return Server(
        id=id, api_url=api_url, cert_sha256=cert_sha256, protocol_type=protocol_type
    )


@pytest.fixture
def mock_processor(mock_outline_server):
    """Фикстура для процессора с патчем."""
    with mock.patch(
        "database.db_processor.DbProcessor.get_server_with_min_users",
        return_value=mock_outline_server,
    ):
        processor = OutlineProcessor()
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
    assert isinstance(mock_processor.session, aiohttp.ClientSession)
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
    key_info = await mock_processor.get_key_info(key.key_id, server_id)
    assert isinstance(key_info, OutlineKey)
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
    rename_status = await mock_processor.rename_key(
        key.key_id, new_key_name, server_id=server_id
    )
    assert rename_status is True
    key_info = await mock_processor.get_key_info(key.key_id, server_id=server_id)
    assert key_info.name == new_key_name


@pytest.mark.asyncio
async def test_get_keys(mock_processor):
    """Тестирование получения списка ключей"""
    key1, server_id = await mock_processor.create_vpn_key()
    key2, server_id = await mock_processor.create_vpn_key()
    key3, server_id = await mock_processor.create_vpn_key()
    try:
        keys = await mock_processor.get_keys(server_id=1)
        assert isinstance(keys, list)
        assert all(key in keys for key in [key1, key2, key3])
    finally:
        await mock_processor.delete_key(key1.key_id, server_id=server_id)
        await mock_processor.delete_key(key2.key_id, server_id=server_id)
        await mock_processor.delete_key(key3.key_id, server_id=server_id)


@pytest.mark.asyncio
async def test_update_data_limit(mock_processor, mock_vpn_key):
    key, server_id = await anext(mock_vpn_key)
    assert key.data_limit == 200 * 1024**3
    new_data_limit = 300 * 10**9
    await mock_processor.update_data_limit(
        key.key_id, new_data_limit, server_id=server_id, key_name=key.name
    )
    key_info = await mock_processor.get_key_info(key.key_id, server_id)
    assert key_info.data_limit == new_data_limit


@pytest.mark.asyncio
async def test_delete_data_limit(mock_processor, mock_vpn_key):
    key, server_id = await anext(mock_vpn_key)
    assert key.data_limit == 200 * 1024**3
    await mock_processor.delete_data_limit(key.key_id, server_id)
    key_info = await mock_processor.get_key_info(key.key_id, server_id)
    assert key_info.data_limit is None
