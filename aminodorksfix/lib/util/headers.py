from copy import deepcopy

from aiohttp import ClientSession
from requests import Session

from aminodorksfix.lib.util import ecdsa, ecdsa_sync, signature

from ...constants import DEFAULT_HEADERS

sid = None
device_id = None


class ApisHeaders:
    def __init__(
        self,
        deviceId: str,
        data: str | bytes | None = None,
        type: str | None = None,
        sig: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ):
        self.__user_id = user_id
        headers = deepcopy(DEFAULT_HEADERS)
        headers["NDCDEVICEID"] = device_id or deviceId
        self.data = data
        if session_id:
            headers["NDCAUTH"] = f"sid={session_id}"
        if type:
            headers["Content-Type"] = type
        if sig:
            headers["NDC-MSG-SIG"] = sig
        if user_id:
            headers["AUID"] = user_id
        if data:
            headers["Content-Length"] = str(len(data))
            headers["NDC-MSG-SIG"] = signature(data)
        self.headers = headers

    def generate_ecdsa_sync(self, session: Session):
        if self.__user_id and isinstance(self.data, str):
            self.headers["NDC-MESSAGE-SIGNATURE"] = ecdsa_sync(
                session, self.data, self.__user_id
            )

    async def generate_ecdsa(self, session: ClientSession):
        if self.__user_id and isinstance(self.data, str):
            self.headers["NDC-MESSAGE-SIGNATURE"] = await ecdsa(
                session, self.data, self.__user_id
            )
