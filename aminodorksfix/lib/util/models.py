from typing import (
    TypedDict,
    NotRequired,
    Dict
)

from .objects import UserProfile

__all__ = ["ClientKwargs", "SubClientKwargs"]


class ClientKwargs(TypedDict):
    certificatePath: NotRequired[bool]
    socket_trace: NotRequired[bool]
    socket_debugging: NotRequired[bool]
    socket_enabled: NotRequired[bool]


class SubClientKwargs(TypedDict):
    profile: UserProfile
    device_id: NotRequired[str]
    proxies: NotRequired[Dict[str, str]]
    certificate_path: NotRequired[bool]