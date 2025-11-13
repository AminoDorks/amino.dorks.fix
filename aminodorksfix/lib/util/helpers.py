from base64 import (
    b64decode,
    b64encode
)
from json import (
    dumps,
    loads
)
from typing import (
    Dict
)

from ...constants import (
    PREFIX,
    SIGNATURE_KEY,
    DEVICE_KEY,
    GENERATOR_HEADERS,
    GENERATOR_URL
)

from os import urandom
from functools import reduce
from hashlib import sha1
from hmac import new
from aiohttp import ClientSession
from requests import Session


def gen_deviceId(data: bytes = None) -> str:
    if isinstance(data, str):
        data = bytes(data, 'utf-8')
    identifier = PREFIX + (data or urandom(20))
    mac = new(DEVICE_KEY, identifier, sha1)
    return f"{identifier.hex()}{mac.hexdigest()}".upper()


def signature(data: str | bytes) -> str:
    data = data if isinstance(data, bytes) \
           else data.encode('utf-8')  # type: ignore
    return b64encode(
        PREFIX + new(SIGNATURE_KEY, data, sha1).digest()
    ).decode("utf-8")


def get_credentials_sync(
        session: Session,
        userId: str
) -> Dict[str, str | int]:
    response = session.get(
        url=f"{GENERATOR_URL}/keymaster/build-credentials/{userId}",
        headers=GENERATOR_HEADERS
    )
    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["credentials"]


async def get_credentials(
        session: ClientSession,
        userId: str
) -> Dict[str, str | int]:
    async with session.get(
        url=f"{GENERATOR_URL}/keymaster/build-credentials/{userId}",
        headers=GENERATOR_HEADERS
    ) as response:
        if response.status != 200:
            raise Exception(await response.text())

        return (await response.json())["credentials"]


def ecdsa_sync(session: Session, data: str, userId: str) -> str:
    data = dumps({
        "payload": data,
        "userId": userId
    })
    response = session.post(
        url=f"{GENERATOR_URL}/keymaster/sign",
        headers=GENERATOR_HEADERS,
        data=data
    )
    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["ecdsa"]


async def ecdsa(session: ClientSession, data: str, userId: str) -> str:
    data = dumps({
        "payload": data,
        "userId": userId
    })
    async with session.post(
        url=f"{GENERATOR_URL}/keymaster/sign",
        headers=GENERATOR_HEADERS,
        data=data
    ) as response:
        if response.status != 200:
            raise Exception(await response.text())

        return (await response.json())["ecdsa"]


def update_deviceId(device: str) -> str:
    return gen_deviceId(bytes.fromhex(device[2:42]))


def decode_sid(sid: str) -> dict:
    return loads(b64decode(reduce(
        lambda a, e: a.replace(
            *e  # type: ignore
        ), ("-+", "_/"), sid + "=" * (-len(sid) % 4)
    ).encode())[1:-20].decode())


def sid_to_uid(SID: str) -> str: return decode_sid(SID)["2"]


def sid_to_ip_address(SID: str) -> str: return decode_sid(SID)["4"]
