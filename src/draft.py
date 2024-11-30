from outline_vpn.outline_vpn import OutlineVPN
import requests
import os

api_url = 'https://5.35.38.7:8811/p78Ho3alpF3e8Sv37eLV1Q'
cert_sha256 = 'CA9E91B93E16E1F160D94D17E2F7C0D0D308858A60F120F6C8C1EDE310E35F64'

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)
keys = client.get_keys()
for x in keys:
 print(x)