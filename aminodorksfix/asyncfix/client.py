from time import (
    timezone,
    sleep
)
from typing import (
    BinaryIO,
    Union,
    Unpack
)
from json import (
    loads,
    dumps
)
from asyncio import (
    get_event_loop,
    new_event_loop
)

from ..constants import (
    API_URL,
    GENERATOR_HEADERS,
    GENDERS_MAP,
    MEDIA_TYPES_MAP,
    SUPPORTED_LANGAUGES,
    COMMENTS_SORTING_MAP
)
from .socket import (
    Callbacks,
    SocketHandler
)
from ..lib.util.exceptions import (
    CheckException,
    AgeTooLow,
    SpecifyType,
    CommunityNotFound,
    WrongType,
    UnsupportedLanguage
)
from ..lib.util.objects import (
    UserProfile,
    CommunityList,
    UserProfileList,
    Community,
    CommentList,
    Membership,
    BlogList,
    WalletHistory,
    WalletInfo,
    FromCode,
    UserProfileCountList
)
from ..lib.util.helpers import (
    gen_deviceId,
    sid_to_uid,
    get_credentials
)

from threading import Thread
from aiohttp import ClientSession
from time import time as timestamp
from locale import getdefaultlocale as locale

from ..lib.util.models import ClientKwargs
from ..lib.util.headers import ApisHeaders
from ..lib.util import headers


class Client(Callbacks, SocketHandler):
    __slots__ = (
        "__api_key",
        "__device_id",
        "__api_proxies",
        "__sid",
        "__account",
        "__active_chat_loops",
        "__stop_loop",
        "_session",
        "_dorks_session",
        "_socket_enabled",
        "_profile"
    )

    def __init__(
            self,
            api_key: str,
            deviceId: str = gen_deviceId(),
            **kwargs: Unpack[ClientKwargs]
    ):
        self.__api_key = api_key
        self.__device_id = deviceId
        
        self._socket_enabled = kwargs.get("socket_enabled", True)
        GENERATOR_HEADERS["Authorization"] = api_key

        SocketHandler.__init__(
            self,
            client=self,
            socket_trace=kwargs.get("socket_trace", False),
            debug=kwargs.get("socket_debugging", False),
            socket_enabled=self._socket_enabled
        )
        Callbacks.__init__(self, self)

        self._profile: UserProfile = UserProfile(None)
        self._session = ClientSession()

    def __del__(self):
        try:
            loop = get_event_loop()
            loop.create_task(self._close_session())
        except RuntimeError:
            loop = new_event_loop()
            loop.run_until_complete(self._close_session())
    
    @property
    def profile(self):
        return self._profile
    
    @property
    def device_id(self):
        return self.__device_id

    async def _close_session(self):
        if not self._session.closed:
            await self._session.close()

    async def _parse_headers(self, data: str = None, type: str = None):
        header = ApisHeaders(deviceId=self.__device_id, data=data, type=type)
        if data:
            await header.generate_ecdsa(self._session)
        return header.headers

    async def join_voice_chat(
            self,
            comId: str,
            chatId: str,
            joinType: int = 1
    ):
        """
        Joins a Voice Chat

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
        """

        self.send(dumps({
            "o": {
                "ndcId": int(comId),
                "threadId": chatId,
                "joinRole": joinType,
                "id": "2154531"
            },
            "t": 112
        }))

    async def join_video_chat(
            self,
            comId: str,
            chatId: str,
            joinType: int = 1
    ):
        """
        Joins a Video Chat

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
        """
        self.send(dumps({
            "o": {
                "ndcId": int(comId),
                "threadId": chatId,
                "joinRole": joinType,
                "channelType": 5,
                "id": "2154531"
            },
            "t": 108
        }))

    async def join_video_chat_as_viewer(self, comId: str, chatId: str):
        self.send(dumps({
            "o":
                {
                    "ndcId": int(comId),
                    "threadId": chatId,
                    "joinRole": 2,
                    "id": "72446"
                },
            "t": 112
        }))

    async def run_vc(self, comId: str, chatId: str, joinType: str):
        while self.active:
            self.send({
                "o": {
                    "ndcId": comId,
                    "threadId": chatId,
                    "joinRole": joinType,
                    "id": "2154531"
                },
                "t": 112
            })
            sleep(1)

    async def start_vc(self, comId: str, chatId: str, joinType: int = 1):
        self.send(dumps({
            "o": {
                "ndcId": comId,
                "threadId": chatId,
                "joinRole": joinType,
                "id": "2154531"
            },
            "t": 112
        }))
        
        self.send(dumps({
            "o": {
                "ndcId": comId,
                "threadId": chatId,
                "channelType": 1,
                "id": "2154531"
            },
            "t": 108
        }))
        self.active = True
        Thread(target=self.run_vc, args=[comId, chatId, joinType])

    async def end_vc(self, comId: str, chatId: str, joinType: int = 2):
        self.active = False
        self.send(dumps({
            "o": {
                "ndcId": comId,
                "threadId": chatId,
                "joinRole": joinType,
                "id": "2154531"
            },
            "t": 112
        }))

    async def verify_yourself(self, email: str, password: str) -> int:
        """
        Passes your IP to account

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

        **Description**
            This function will verify your ip of this account
            and return the status code of the response.

        **Example**
            >>> await client.verify_yourself("example@example.com", "password")
            200
        """
        data = dumps({
            "email": email,
            "v": 2,
            "secret": f"0 {password}",
            "deviceID": self.__device_id,
            "clientType": 300,
            "action": "normal",
            "timestamp": int(timestamp() * 1000)
        })
        async with self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=await self._parse_headers(data=data),
            data=data
        ) as response:
            if response.status != 200:
                CheckException(response.text)

            return response.status
    
    async def __update_public_key(self):
        data = dumps(await get_credentials(
            self._session,
            str(self._profile.userId)  # stub
        ))
        async with self._session.post(
            url=f"{API_URL}/g/s/security/public_key",
            headers=await self._parse_headers(data=data), data=data
        ) as response:
            if response.status != 200:
                CheckException(await response.text())
            return 200

    async def login_sid(self, SID: str):
        """
        Login into an account with an SID

        **Parameters**
            - **SID** : SID of the account
        """

        self._profile: UserProfile = await self.get_user_info(sid_to_uid(SID))
        self._profile.api_key = self.__api_key
        headers.sid = SID
        headers.userId = self._profile.userId
        await self.__update_public_key()

    async def login(self, email: str, password: str):
        """
        Login into an account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "email": email,
            "v": 2,
            "secret": f"0 {password}",
            "deviceID": self.__device_id,
            "clientType": 100,
            "action": "normal",
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=await self._parse_headers(data=data), data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())
            else:
                self.authenticated = True
                self.json = loads(await response.text())
                self.sid = self.json["sid"]
                self.userId = self.json["account"]["uid"]
                self._profile: UserProfile = UserProfile(
                    self.json["userProfile"]
                ).UserProfile
                self._profile.api_key = self.__api_key
                headers.sid = self.sid
                headers.userId = self.userId

                await self.__update_public_key()
                if self._socket_enabled:
                    self.run_amino_socket()
                return loads(await response.text())

    async def login_phone(self, phoneNumber: str, password: str):
        """
        Login into an account.

        **Parameters**
            - **phoneNumber** : Phone number of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "phoneNumber": phoneNumber,
            "v": 2,
            "secret": f"0 {password}",
            "deviceID": self.__device_id,
            "clientType": 100,
            "action": "normal",
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=await self._parse_headers(data=data), data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())
            else:
                self.authenticated = True
                self.json = loads(await response.text())
                self.sid = self.json["sid"]
                self.userId = self.json["account"]["uid"]
                self._profile: UserProfile = UserProfile(
                    self.json["userProfile"]
                ).UserProfile
                self._profile.api_key = self.__api_key
                self.secret = self.json["secret"]
                headers.sid = self.sid
                headers.userId = self.userId
                await self.__update_public_key()
                if self._socket_enabled:
                    self.run_amino_socket()
                return loads(await response.text())

    async def login_secret(self, secret: str):
        """
        Login into an account.

        **Parameters**
            - **secret** : Secret of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "v": 2,
            "secret": secret,
            "deviceID": self.__device_id,
            "clientType": 100,
            "action": "normal",
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=await self._parse_headers(data=data), data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())
            else:
                self.authenticated = True
                self.json = loads(await response.text())
                self.sid = self.json["sid"]
                self.userId = self.json["account"]["uid"]
                self._profile: UserProfile = UserProfile(
                    self.json["userProfile"]
                ).UserProfile
                self._profile.api_key = self.__api_key
                headers.sid = self.sid
                headers.userId = self.userId
                await self.__update_public_key()
                if self._socket_enabled:
                    self.run_amino_socket()
                return loads(await response.text())

    async def restore(self, email: str, password: str):
        """
        Restore a deleted account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "secret": f"0 {password}",
            "deviceID": self.__device_id,
            "email": email,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/account/delete-request/cancel", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

           
                return response.status

    async def logout(self):
        """
        Logout from an account.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "deviceID": self.__device_id,
            "clientType": 100,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/auth/logout", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

           
                self.authenticated = False
                self.json = None
                self.sid = None
                self.userId = None
                self.account: None
                self.profile: None
                headers.sid = None
                self.close()
                await self._session.close()
                return response.status

    async def configure(self, age: int, gender: str):
        """
        Configure the settings of an account.

        **Parameters**
            - **age** : Age of the account. Minimum is 13.
            - **gender** : Gender of the account.
                - ``Male``, ``Female`` or ``Non-Binary``

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        gender_from_map = GENDERS_MAP.get(gender)

        if not gender_from_map:
            raise SpecifyType()
        if age <= 12:
            raise AgeTooLow()

        data = dumps({
            "age": age,
            "gender": gender_from_map,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/persona/profile/basic", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def verify(self, email: str, code: str):
        """
        Verify an account.

        **Parameters**
            - **email** : Email of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "validationContext": {
                "type": 1,
                "identity": email,
                "data": {"code": code}},
            "deviceID": self.__device_id,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/auth/check-security-validation", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def request_verify_code(self, email: str, resetPassword: bool = False):
        """
        Request an verification code to the targeted email.

        **Parameters**
            - **email** : Email of the account.
            - **resetPassword** : If the code should be for Password Reset.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = {
            "identity": email,
            "type": 1,
            "deviceID": self.__device_id
        }

        if resetPassword is True:
            data["level"] = 2
            data["purpose"] = "reset-password"

        data = dumps(data)
        async with self._session.post(f"{API_URL}/g/s/auth/request-security-validation", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def activate_account(self, email: str, code: str):
        """
        Activate an account.

        **Parameters**
            - **email** : Email of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "type": 1,
            "identity": email,
            "data": {"code": code},
            "deviceID": self.__device_id
        })

        async with self._session.post(f"{API_URL}/g/s/auth/activate-email", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    # Provided by "𝑰 𝑵 𝑻 𝑬 𝑹 𝑳 𝑼 𝑫 𝑬#4082"
    async def delete_account(self, password: str):
        """
        Delete an account.

        **Parameters**
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "deviceID": self.__device_id,
            "secret": f"0 {password}"
        })

        async with self._session.post(f"{API_URL}/g/s/account/delete-request", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def change_password(self, email: str, password: str, code: str):
        """
        Change password of an account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "updateSecret": f"0 {password}",
            "emailValidationContext": {
                "data": {
                    "code": code
                },
                "type": 1,
                "identity": email,
                "level": 2,
                "deviceID": self.__device_id
            },
            "phoneNumberValidationContext": None,
            "deviceID": self.__device_id
        })

        async with self._session.post(f"{API_URL}/g/s/auth/reset-password", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def check_device(self, deviceId: str):
        """
        Check if the Device ID is valid.

        **Parameters**
            - **deviceId** : ID of the Device.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "deviceID": deviceId,
            "bundleID": "com.narvii.amino.master",
            "clientType": 100,
            "timezone": -timezone // 1000,
            "systemPushEnabled": True,
            "locale": locale()[0],
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/device", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_account_info(self):
        async with self._session.get(f"{API_URL}/g/s/account", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfile(loads(await response.text())["account"]).UserProfile

    async def upload_media(self, file: BinaryIO, fileType: str):
        """
        Upload file to the amino servers.

        **Parameters**
            - **file** : File to be uploaded.

        **Returns**
            - **Success** : Url of the file uploaded to the server.

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        type_from_map = MEDIA_TYPES_MAP.get(fileType)
        if not type_from_map:
            raise SpecifyType(fileType)

        data = file.read()

        async with self._session.post(f"{API_URL}/g/s/media/upload", headers=ApisHeaders(type=type_from_map, data=data, deviceId=self.__device_id).headers, data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["mediaValue"]

    def handle_socket_message(self, data):
        return self.resolve(data)

    async def get_eventlog(self, language: str = "en"):
        async with self._session.get(f"{API_URL}/g/s/eventlog/profile?language={language}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())

    async def sub_clients(self, start: int = 0, size: int = 25):
        """
        List of Communities the account is in.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Community List <aminofixasync.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/community/joined?v=1&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return CommunityList(loads(await response.text())["communityList"]).CommunityList

    async def sub_clients_profile(self, start: int = 0, size: int = 25):
        async with self._session.get(f"{API_URL}/g/s/community/joined?v=1&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["communityList"]

    async def get_user_info(self, userId: str):
        """
        Information of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`User Object <aminofixasync.lib.util.UserProfile>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfile(loads(await response.text())["userProfile"]).UserProfile

    async def get_community_info(self, comId: str):
        """
        Information of an Community.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : :meth:`Community Object <aminofixasync.lib.util.Community>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s-x{comId}/community/info?withInfluencerList=1&withTopicList=true&influencerListOrderStrategy=fansCount", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return Community(loads(await response.text())["community"]).Community

    async def search_community(self, aminoId: str):
        """
        Search a Community byt its Amino ID.

        **Parameters**
            - **aminoId** : Amino ID of the Community.

        **Returns**
            - **Success** : :meth:`Community List <aminofixasync.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/search/amino-id-and-link?q={aminoId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

           
            response = loads(await response.text())["resultList"]
            if len(response) == 0:
                raise CommunityNotFound(aminoId)
            
            return CommunityList([com["refObject"] for com in response]).CommunityList

    async def get_user_following(self, userId: str, start: int = 0, size: int = 25):
        """
        List of Users that the User is Following.

        **Parameters**
            - **userId** : ID of the User.
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User List <aminofixasync.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}/joined?start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfileList(loads(await response.text())["userProfileList"]).UserProfileList

    async def get_user_followers(self, userId: str, start: int = 0, size: int = 25):
        """
        List of Users that are Following the User.

        **Parameters**
            - **userId** : ID of the User.
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User List <aminofixasync.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}/member?start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfileList(loads(await response.text())["userProfileList"]).UserProfileList

    async def get_blocked_users(self, start: int = 0, size: int = 25):
        """
        List of Users that the User Blocked.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Users List <aminofixasync.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/block?start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfileList(loads(await response.text())["userProfileList"]).UserProfileList

    async def get_blocker_users(self, start: int = 0, size: int = 25):
        """
        List of Users that are Blocking the User.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`List of User IDs <None>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/block/full-list?start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["blockerUidList"]

    async def get_wall_comments(self, userId: str, sorting: str, start: int = 0, size: int = 25):
        """
        List of Wall Comments of an User.

        **Parameters**
            - **userId** : ID of the User.
            - **sorting** : Order of the Comments.
                - ``newest``, ``oldest``, ``top``
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Comments List <aminofixasync.lib.util.CommentList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        sorting_type = COMMENTS_SORTING_MAP.get(sorting)
        if not sorting_type:
            raise WrongType(sorting)

        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}/g-comment?sort={sorting}&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return CommentList(loads(await response.text())["commentList"]).CommentList

    async def flag(self, reason: str, flagType: int, userId: str = None, blogId: str = None, wikiId: str = None, asGuest: bool = False):
        """
        Flag a User, Blog or Wiki.

        **Parameters**
            - **reason** : Reason of the Flag.
            - **flagType** : Type of the Flag.
            - **userId** : ID of the User.
            - **blogId** : ID of the Blog.
            - **wikiId** : ID of the Wiki.
            - *asGuest* : Execute as a Guest.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "flagType": flagType,
            "message": reason,
            "objectId": userId,
            "objectType": 0,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/{"g-flag" if asGuest else "flag"}", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def follow(self, userId: Union[str, list]):
        """
        Follow an User or Multiple Users.

        **Parameters**
            - **userId** : ID of the User or List of IDs of the Users.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        if isinstance(userId, str):
            async with self._session.post(f"{API_URL}/g/s/user-profile/{userId}/member", headers=await self._parse_headers()) as response:
                if response.status != 200:
                    return CheckException(await response.text())

                return response.status

        elif isinstance(userId, list):
            data = dumps({"targetUidList": userId, "timestamp": int(timestamp() * 1000)})

            async with self._session.post(f"{API_URL}/g/s/user-profile/{self.userId}/joined", headers=await self._parse_headers(data=data), data=data) as response:
                if response.status != 200:
                    return CheckException(await response.text())

                return response.status

    async def unfollow(self, userId: str):
        """
        Unfollow an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.delete(f"{API_URL}/g/s/user-profile/{userId}/member/{self.userId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def block(self, userId: str):
        """
        Block an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.post(f"{API_URL}/g/s/block/{userId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def unblock(self, userId: str):
        """
        Unblock an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.delete(f"{API_URL}/g/s/block/{userId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def join_community(self, comId: str, invitationCode: str = None):
        """
        Join a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **invitationCode** : Invitation Code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = {}
        if invitationCode:
            data["invitationId"] = (await self.link_identify(invitationCode))["invitation"]["invitationId"]
        
        data["timestamp"] = int(timestamp() * 1000)
        data = dumps(data)

        async with self._session.post(f"{API_URL}/x{comId}/s/community/join", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def request_join_community(self, comId: str, message: str = None):
        """
        Request to join a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **message** : Message to be sent.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({"message": message, "timestamp": int(timestamp() * 1000)})

        async with self._session.post(f"{API_URL}/x{comId}/s/community/membership-request", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def leave_community(self, comId: str):
        """
        Leave a Community.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.post(f"{API_URL}/x{comId}/s/community/leave", headers=await self._parse_headers(type="application/x-www-form-urlencoded")) as response:
            if response.status != 200:
                return CheckException(await response.text())
            else:
                return response.status

    async def flag_community(self, comId: str, reason: str, flagType: int, isGuest: bool = False):
        """
        Flag a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **reason** : Reason of the Flag.
            - **flagType** : Type of Flag.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "objectId": comId,
            "objectType": 16,
            "flagType": flagType,
            "message": reason,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/x{comId}/s/{"g-flag" if isGuest else "flag"}", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def edit_profile(self, nickname: str = None, content: str = None, icon: BinaryIO = None, backgroundColor: str = None, backgroundImage: str = None, defaultBubbleId: str = None, fileType: str = "image"):
        """
        Edit account's Profile.

        **Parameters**
            - **nickname** : Nickname of the Profile.
            - **content** : Biography of the Profile.
            - **icon** : Icon of the Profile.
            - **backgroundImage** : Url of the Background Picture of the Profile.
            - **backgroundColor** : Hexadecimal Background Color of the Profile.
            - **defaultBubbleId** : Chat bubble ID.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = {
            "address": None,
            "latitude": 0,
            "longitude": 0,
            "mediaList": None,
            "eventSource": "UserProfileView",
            "timestamp": int(timestamp() * 1000)
        }

        if nickname:
            data["nickname"] = nickname
        if icon:
            data["icon"] = await self.upload_media(icon, fileType)
        if content:
            data["content"] = content
        if backgroundColor:
            data["extensions"] = {"style": {"backgroundColor": backgroundColor}}
        if backgroundImage:
            data["extensions"] = {"style": {"backgroundMediaList": [[100, backgroundImage, None, None, None]]}}
        if defaultBubbleId:
            data["extensions"] = {"defaultBubbleId": defaultBubbleId}

        data = dumps(data)

        async with self._session.post(f"{API_URL}/g/s/user-profile/{self.userId}", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def set_privacy_status(self, isAnonymous: bool = False, getNotifications: bool = False):
        """
        Edit account's Privacy Status.

        **Parameters**
            - **isAnonymous** : If visibility should be Anonymous or not.
            - **getNotifications** : If account should get new Visitors Notifications.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = dumps({
            "timestamp": int(timestamp() * 1000),
            "privacyMode": int(isAnonymous),
            "notificationStatus": int(getNotifications)
        })

        async with self._session.post(f"{API_URL}/g/s/account/visit-settings", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def set_amino_id(self, aminoId: str):
        """
        Edit account's Amino ID.

        **Parameters**
            - **aminoId** : Amino ID of the Account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({"aminoId": aminoId, "timestamp": int(timestamp() * 1000)})

        async with self._session.post(f"{API_URL}/g/s/account/change-amino-id", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_linked_communities(self, userId: str):
        """
        Get a List of Linked Communities of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`Community List <aminofixasync.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}/linked-community", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return CommunityList(loads(await response.text())["linkedCommunityList"]).CommunityList

    async def get_unlinked_communities(self, userId: str):
        """
        Get a List of Unlinked Communities of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`Community List <aminofixasync.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile/{userId}/linked-community", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return CommunityList(loads(await response.text())["unlinkedCommunityList"]).CommunityList

    async def reorder_linked_communities(self, comIds: list):
        """
        Reorder List of Linked Communities.

        **Parameters**
            - **comIds** : IDS of the Communities.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({"ndcIds": comIds, "timestamp": int(timestamp() * 1000)})

        async with self._session.post(f"{API_URL}/g/s/user-profile/{self.userId}/linked-community/reorder", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def add_linked_community(self, comId: str):
        """
        Add a Linked Community on your profile.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.post(f"{API_URL}/g/s/user-profile/{self.userId}/linked-community/{comId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def remove_linked_community(self, comId: str):
        """
        Remove a Linked Community on your profile.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.delete(f"{API_URL}/g/s/user-profile/{self.userId}/linked-community/{comId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def comment(self, message: str, userId: str = None, replyTo: str = None):
        """
        Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **message** : Message to be sent.
            - **userId** : ID of the User. (for Walls)
            - **blogId** : ID of the Blog. (for Blogs)
            - **wikiId** : ID of the Wiki. (for Wikis)
            - **replyTo** : ID of the Comment to Reply to.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """

        data = {
            "content": message,
            "stickerId": None,
            "type": 0,
            "timestamp": int(timestamp() * 1000),
            "eventSource": "UserProfileView"
        }

        if replyTo:
            data["respondTo"] = replyTo
        
        data = dumps(data)

        async with self._session.post(f"{API_URL}/g/s/user-profile/{userId}/g-comment", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def delete_comment(self, commentId: str, userId: str):
        """
        Delete a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.delete(url=f"{API_URL}/g/s/user-profile/{userId}/g-comment/{commentId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def like_comment(self, commentId: str, userId: str):
        """
        Like a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "value": 4,
            "timestamp": int(timestamp() * 1000),
            "eventSource": "UserProfileView"
        })

        async with self._session.post(f"{API_URL}/g/s/user-profile/{userId}/comment/{commentId}/g-vote?cv=1.2&value=1", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def unlike_comment(self, commentId: str, userId: str):
        """
        Remove a like from a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.delete(url=f"{API_URL}/g/s/user-profile/{userId}/comment/{commentId}/g-vote?eventSource=UserProfileView", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_membership_info(self):
        """
        Get Information about your Amino+ Membership.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`Membership Object <aminofixasync.lib.util.Membership>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/membership?force=true", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return Membership(loads(await response.text())).Membership

    async def get_ta_announcements(self, language: str = "en", start: int = 0, size: int = 25):
        """
        Get the list of Team Amino's Announcement Blogs.

        **Parameters**
            - **language** : Language of the Blogs.
                - ``en``, ``es``, ``pt``, ``ar``, ``ru``, ``fr``, ``de``
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Blogs List <aminofixasync.lib.util.BlogList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        if language not in SUPPORTED_LANGAUGES:
            raise UnsupportedLanguage(language)

        async with self._session.get(f"{API_URL}/g/s/announcement?language={language}&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return BlogList(loads(await response.text())["blogList"]).BlogList

    async def get_wallet_info(self):
        """
        Get Information about the account's Wallet.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`Wallet Object <aminofixasync.lib.util.WalletInfo>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/wallet", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return WalletInfo(loads(await response.text())["wallet"]).WalletInfo

    async def get_wallet_history(self, start: int = 0, size: int = 25):
        """
        Get the Wallet's History Information.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Wallet Object <aminofixasync.lib.util.WalletInfo>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/wallet/coin/history?start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return WalletHistory(loads(await response.text())["coinHistoryList"]).WalletHistory

    async def get_from_deviceid(self, deviceId: str):
        """
        Get the User ID from an Device ID.

        **Parameters**
            - **deviceID** : ID of the Device.

        **Returns**
            - **Success** : :meth:`User ID <aminofixasync.lib.util.UserProfile.userId>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/auid?deviceId={deviceId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["auid"]

    async def get_from_code(self, code: str):
        """
        Get the Object Information from the Amino URL Code.

        **Parameters**
            - **code** : Code from the Amino URL.

        **Returns**
            - **Success** : :meth:`From Code Object <aminofixasync.lib.util.FromCode>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/link-resolution?q={code}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return FromCode(loads(await response.text())["linkInfoV2"]).FromCode

    async def get_supported_languages(self):
        """
        Get the List of Supported Languages by Amino.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`List of Supported Languages <List>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/community-collection/supported-languages?start=0&size=100", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["supportedLanguages"]

    async def claim_new_user_coupon(self):
        """
        Claim the New User Coupon available when a new account is created.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.post(f"{API_URL}/g/s/coupon/new-user-coupon/claim", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_subscriptions(self, start: int = 0, size: int = 25):
        """
        Get Information about the account's Subscriptions.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`List <List>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/store/subscription?objectType=122&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())["storeSubscriptionItemList"]

    async def get_all_users(self, start: int = 0, size: int = 25):
        """
        Get list of users of Amino.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User Profile Count List Object <aminofixasync.lib.util.UserProfileCountList>`

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        async with self._session.get(f"{API_URL}/g/s/user-profile?type=recent&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfileCountList(loads(await response.text())).UserProfileCountList

    # Contributed by 'https://github.com/LynxN1'
    async def link_identify(self, code: str):
        async with self._session.get(f"{API_URL}/g/s/community/link-identify?q=http%3A%2F%2Faminoapps.com%2Finvite%2F{code}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())

    async def wallet_config(self, level: int):
        """
        Changes ads config

        **Parameters**
            - **level** - Level of the ads.
                - ``1``, ``2``

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminofixasync.lib.util.exceptions>`
        """
        data = dumps({
            "adsLevel": level,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(f"{API_URL}/g/s/wallet/ads/config", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status
