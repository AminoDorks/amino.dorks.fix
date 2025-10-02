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
    socketDebugging: NotRequired[bool]
    socket_enabled: NotRequired[bool]


class SubClientKwargs(TypedDict):
    profile: UserProfile
    deviceId: NotRequired[str]
    proxies: NotRequired[Dict[str, str]]
    certificatePath: NotRequired[bool]
