__title__ = "amino.dorks.fix"
__author__ = "misterio060"
__license__ = "MIT"
__copyright__ = "Copyright 2025 misterio060"
__version__ = "3.9.10.14"

__all__ = [
    "ACM",
    "Client",
    "SubClient",
    "exceptions",
    "helpers",
    "objects",
    "headers",
    "acm",
    "client",
    "sub_client",
    "socket",
    "Callbacks",
    "SocketHandler",
]

from json import loads

from requests import get

from .acm import ACM
from .asyncfix import acm, client, socket, sub_client
from .client import Client
from .lib.util import exceptions, headers, helpers, objects
from .socket import Callbacks, SocketHandler
from .sub_client import SubClient

__newest__ = loads(get("https://pypi.org/pypi/amino.dorks.fix/json").text)["info"][
    "version"
]

if __version__ != __newest__:
    print(
        f"New version of {__title__}" + f"available: {__newest__} (Using {__version__})"
    )
    print("Visit our Telegram channel - https://t.me/aminodorks")
