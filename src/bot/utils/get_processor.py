from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.vless_processor_init import vless_processor


async def get_processor(vpn_type: str):
    vpn_type = vpn_type.lower()
    processors = {"outline": outline_processor, "vless": vless_processor}
    return processors.get(vpn_type.lower())
