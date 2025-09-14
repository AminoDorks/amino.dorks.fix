import json
import os

from functools import reduce
from base64 import b64decode, b64encode
from typing import Union
from hashlib import sha1
from hmac import new
from aiohttp import ClientSession
from requests import Session
PREFIX = bytes.fromhex("52")
SIG_KEY = bytes.fromhex("EAB4F1B9E3340CD1631EDE3B587CC3EBEDF1AFA9")
DEVICE_KEY = bytes.fromhex("AE49550458D8E7C51D566916B04888BFB8B3CA7D")

gen_headers = {
    "Content-Type": "application/json; charset=utf8",
    "CONNECTION": "Keep-Alive",
    "Authorization": None
}
celt_is_god_api_xxx="https://aminodorks.agency/api/v1"


def gen_deviceId(data: bytes = None) -> str:
    if isinstance(data, str): data = bytes(data, 'utf-8')
    identifier = PREFIX + (data or os.urandom(20))
    mac = new(DEVICE_KEY, identifier, sha1)
    return f"{identifier.hex()}{mac.hexdigest()}".upper()

def signature(data: Union[str, bytes]) -> str:
    data = data if isinstance(data, bytes) else data.encode("utf-8")
    return b64encode(PREFIX + new(SIG_KEY, data, sha1).digest()).decode("utf-8")
#
def get_certs(session: Session, userId: str):
    response=session.get(f"{celt_is_god_api_xxx}/signature/credentials/{userId}",headers=gen_headers)
    if response.status_code !=200:
        raise Exception(response.text)
    return response.json()["credentials"]

async def get_certs_a(session: ClientSession, userId: str):
    async with session.get(f"{celt_is_god_api_xxx}/signature/credentials/{userId}",headers=gen_headers) as response:
        if response.status !=200:
            raise Exception(await response.text())
        return (await response.json())["credentials"]

def new_sig(session: Session, data: str, userId: str):
    data=json.dumps({
        "payload":data,
        "userId":userId
    })
    response=session.post(f"{celt_is_god_api_xxx}/signature/ecdsa",headers=gen_headers,data=data)
    if response.status_code !=200:
        raise Exception(response.text)
    return response.json()["ECDSA"]

async def new_sig_a(session: ClientSession, data: str, userId: str):
    data=json.dumps({
        "payload":data,
        "userId":userId
    })
    async with session.post(f"{celt_is_god_api_xxx}/signature/ecdsa",headers=gen_headers,data=data) as response:
        if response.status !=200:
            raise Exception(await response.text())
        return (await response.json())["ECDSA"]

def update_deviceId(device: str) -> str:
    return gen_deviceId(bytes.fromhex(device[2:42]))

def decode_sid(sid: str) -> dict:
    return json.loads(b64decode(reduce(lambda a, e: a.replace(*e), ("-+", "_/"), sid + "=" * (-len(sid) % 4)).encode())[1:-20].decode())

def sid_to_uid(SID: str) -> str: return decode_sid(SID)["2"]

def sid_to_ip_address(SID: str) -> str: return decode_sid(SID)["4"]