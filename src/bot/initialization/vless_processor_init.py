import os

from dotenv import load_dotenv

from bot.processors.vless_processor import VlessPocessor

load_dotenv()

vless_ip = os.getenv("VLESS_IP")
vless_password = os.getenv("VLESS_PASSWORD")

vless_processor = VlessPocessor(ip=vless_ip, password=vless_password)


"""
# Добавляем нового клиента
ok, link_or_msg = vless.add_or_update_key('TEST_1')
if ok:
    logger.info(f"Ключ добавлен, ссылка: {link_or_msg}")
else:
    logger.warning(f"Ошибка при добавлении: {link_or_msg}")

# ok, link_or_msg = vless.add_or_update_key('TEST_2')
# if ok:
#     logger.info(f"Ключ добавлен, ссылка: {link_or_msg}")
# else:
#     logger.warning(f"Ошибка при добавлении: {link_or_msg}")

# Выводим список активных
# actives = vless.activ_list()
# logger.info(f"Список активных ключей: {actives}")
time.sleep(5)
# Удаляем ключ
ok, msg = vless.delete_key('TEST_1')
if ok:
    logger.info(f"Ключ TEST_1 удалён успешно")
else:
    logger.warning(f"Ошибка при удалении ключа: {msg}")

"""
