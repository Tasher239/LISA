from outline_vpn.outline_vpn import OutlineVPN
import requests
import os

api_url = "https://5.35.38.7:8811/p78Ho3alpF3e8Sv37eLV1Q"
cert_sha256 = "CA9E91B93E16E1F160D94D17E2F7C0D0D308858A60F120F6C8C1EDE310E35F64"

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)


def create_new_key(
    key_id: str = "100", name: str = "new_key", data_limit_gb: float = 0
):
    return client.create_key(key_id=key_id, name=name, data_limit=data_limit_gb)


#
# keys_lst = client.get_keys()
# print(len(keys_lst))
# status = create_new_key()
# print(status)
# print(type(status.key_id))

keys_lst = client.get_keys()
print(keys_lst)
