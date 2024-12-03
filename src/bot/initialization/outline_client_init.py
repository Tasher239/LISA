import os
from outline_vpn.outline_vpn import OutlineVPN
from dotenv import load_dotenv
from bot.utils.outline_processor import OutlineProcessor

load_dotenv()

api_url = os.getenv("API_URL")
cert_sha256 = os.getenv("CERT_SHA")

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)
outline_processor = OutlineProcessor(client)
