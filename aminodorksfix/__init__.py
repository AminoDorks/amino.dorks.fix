__title__ = 'amino.dorks.fix'
__author__ = 'misterio060'
__license__ = 'MIT'
__copyright__ = 'Copyright 2025 misterio060'
__version__ = '3.7.5.5'

from .acm import ACM
from .client import Client
from .sub_client import SubClient
from .lib.util import exceptions, helpers, objects, headers
from .asyncfix import acm, client, sub_client, socket
from .socket import Callbacks, SocketHandler
from requests import get
from json import loads

__newest__ = loads(get("https://pypi.org/pypi/amino.dorks.fix/json").text)["info"]["version"]

if __version__ != __newest__:
    print(f"New version of {__title__} available: {__newest__} (Using {__version__})")
    print("Visit our Telegram channel - https://t.me/aminodorks")
