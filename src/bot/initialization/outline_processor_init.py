import os
import sys

sys.path.append("/Users/aydar/Desktop/VPN2_2/lib/python3.11/site-packages")
from outline_vpn.outline_vpn import OutlineVPN
from dotenv import load_dotenv
from src.bot.utils.outline_processor import OutlineProcessor

load_dotenv()

api_url = os.getenv("API_URL")
cert_sha256 = os.getenv("CERT_SHA")

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)
outline_processor = OutlineProcessor(client)
