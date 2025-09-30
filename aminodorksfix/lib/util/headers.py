from aiohttp import ClientSession
from requests import Session
from copy import deepcopy

from ...constants import DEFAULT_HEADERS

from aminodorksfix.lib.util import (
    signature,
    new_sig,
    new_sig_a
)

sid = None
device_id = None
userId = None


class ApisHeaders:
    def __init__(
            self,
            deviceId: str,
            data: str | bytes = None,
            type: str = None,
            sig: str = None
    ):

        headers = deepcopy(DEFAULT_HEADERS)
        headers["NDCDEVICEID"] = device_id or deviceId
        self.data = data
        if sid:
            headers["NDCAUTH"] = f"sid={sid}"
        if type:
            headers["Content-Type"] = type
        if sig:
            headers["NDC-MSG-SIG"] = sig
        if userId:
            headers["AUID"] = userId
        if data:
            headers["Content-Length"] = str(len(data))
            headers["NDC-MSG-SIG"] = signature(data)
        self.headers = headers

    def generate_ecdsa_sync(self, session: Session):
        if userId and isinstance(self.data, str):
            self.headers["NDC-MESSAGE-SIGNATURE"] = new_sig(
                session,
                self.data,
                userId
            )

    async def async_h(self, session: ClientSession):
        if userId and isinstance(self.data, str):
            self.headers["NDC-MESSAGE-SIGNATURE"] = await new_sig_a(
                session,
                self.data,
                userId
            )
