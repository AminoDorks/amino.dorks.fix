from time import (
    timezone,
    sleep,
    time as timestamp
)
from typing import (
    BinaryIO,
    Unpack,
    Dict,
    Any,
    List
)
from json import (
    loads,
    dumps
)

from .socket import (
    Callbacks,
    SocketHandler
)
from .lib.util.exceptions import (
    CheckException,
    AgeTooLow,
    SpecifyType,
    CommunityNotFound,
    WrongType,
    UnsupportedLanguage
)
from .constants import (
    API_URL,
    GENDERS_MAP,
    MEDIA_TYPES_MAP,
    COMMENTS_SORTING_MAP,
    SUPPORTED_LANGAUGES,
    GENERATOR_HEADERS
)
from .lib.util.helpers import (
    gen_deviceId,
    sid_to_uid,
    get_credentials_sync
)
from .lib.util.objects import (
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

from locale import getdefaultlocale
from requests import Session
from threading import Thread

from .lib.util.models import ClientKwargs
from .lib.util.headers import ApisHeaders
from .lib.util import headers


class Client(Callbacks, SocketHandler):
    __slots__ = (
        "__api_key",
        "__device_id",
        "__proxies",
        "__api_proxies",
        "__certificate_path",
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
            proxies: dict = None,
            **kwargs: Unpack[ClientKwargs]
    ) -> None:
        """
        Initialize a Client object.

        Parameters:
        api_key (str): The API key from the AminoDorks.
        deviceId (str): The device ID to use for API requests.
                                         Defaults to a generated UUID.
        userAgent (str): The User-Agent string to use for API requests.
                                         Defaults to USER_AGENT variable.
        proxies (dict): A dictionary of proxies to use for API requests.
                                         Defaults to None.
        socket_enabled (bool): Whether the SocketHandler should be enabled.
                                         Defaults to True.
        proxies (dict): A dictionary of proxies to use for API requests.
                                         Defaults to None.
        certificatePath (str): The path to the certificate file to use
                                         for API requests. Defaults to None.

        Returns:
        None
        """
        SocketHandler.__init__(
            self,
            client=self,
            socket_trace=kwargs.get("socket_trace", False),
            debug=kwargs.get("socket_debugging", False),
            socket_enabled=kwargs.get("socket_enabled", True)
        )
        Callbacks.__init__(self, self)
        self._session = Session()
        self._dorks_session = Session()
        self.__api_key = api_key
        self.__device_id = deviceId
        self.__proxies = proxies
        self.__certificate_path = kwargs.get("certificate_path")
        self.__active_live_chats = []
        self.__stop_loop = False
        self.__sid = None
        self._socket_enabled = kwargs.get("socket_enabled")
        self._profile: UserProfile = UserProfile(None)
        GENERATOR_HEADERS["Authorization"] = api_key

    @property
    def profile(self) -> UserProfile:
        return self._profile

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def sid(self) -> str | None:
        return self.__sid

    def _parse_headers(
            self,
            data: str = None,
            type: str = None
    ) -> Dict[str, str]:
        """
        Generates the headers for a request.

        **data** : The data to sign
        **type** : The type of the request

        **Returns**
            - **Dict[str, str]** : The headers for the request
        """
        header = ApisHeaders(
            deviceId=self.__device_id,
            data=data,
            type=type
        )
        header.generate_ecdsa_sync(self._dorks_session)

        return header.headers

    def __update_public_key(self) -> int | None:
        """
        Updates the public key for the user.

        **Returns**
            - **200** : Success
            - **None** : If the user ID is not set

        **Raises**
            - **CheckException** : If the server returns an error
        """
        if not self._profile.userId:
            return

        data = dumps(
            get_credentials_sync(
                self._session,
                self._profile.userId
            )
        )
        response = self._session.post(
            url=f"{API_URL}/g/s/security/public_key",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            CheckException(response.text)
        return 200

    def join_voice_chat(
            self,
            comId: str,
            chatId: str,
            joinType: int = 1
    ) -> None:
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

    def join_video_chat(
            self,
            comId: str,
            chatId: str,
            joinType: int = 1
    ) -> None:
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

    def join_video_chat_as_viewer(self, comId: str, chatId: str) -> None:
        """
        Joins a Video Chat as a Viewer

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
        """
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

    def leave_from_live_chat(self, chatId: str) -> None:
        """
        Leaves a Live Chat

        **Parameters**
            - **chatId** : ID of the Chat

        **Description**
            This function will remove the chat from the list of
                                               active live chats.

        **Returns**
            - **None** : None
        """
        if chatId in self.__active_live_chats:
            self.__active_live_chats.remove(chatId)

    def run_vc(self, comId: str, chatId: str, joinType: int) -> None:
        """
        Runs a Voice Chat

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
            - **joinType** : Type of the Join (1 = Join, 2 = View)

        **Description**
            This function will send a join request to a Voice Chat
                                                   every 60 seconds.

        **Returns**
            - **None** : None
        """
        while chatId in self.__active_live_chats and not self.__stop_loop:
            self.send(dumps({
                "o": {
                    "ndcId": int(comId),
                    "threadId": chatId,
                    "joinRole": joinType,
                    "id": "2154531"
                },
                "t": 112
            }))
            sleep(60)

            if self.stop_loop:
                break

    def start_vc(self, comId: str, chatId: str, joinType: int = 1) -> None:
        """
        Starts a Voice Chat

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
            - **joinType** : Type of the Join (1 = Join, 2 = View)
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

        self.send(dumps({
            "o": {
                "ndcId": int(comId),
                "threadId": chatId,
                "channelType": 1,
                "id": "2154531"
            },
            "t": 108
        }))

        self.__active_live_chats.append(chatId)
        Thread(target=lambda: self.run_vc(
            comId, chatId, joinType
        )).start()

    def end_vc(self, comId: str, chatId: str, joinType: int = 2) -> None:
        """
        Ends a Voice Chat

        **Parameters**
            - **comId** : ID of the Community
            - **chatId** : ID of the Chat
            - **joinType** : Join Type of the Voice Chat (default: 2)

        **Returns**
            - **None** : None
        """
        self.leave_from_live_chat(chatId)

        self.send(dumps({
            "o": {
                "ndcId": int(comId),
                "threadId": chatId,
                "joinRole": joinType,
                "id": "2154531"
            },
            "t": 112
        }))
        self.__active_live_chats.remove(chatId)
        self.stop_loop = True

    def login_sid(self, SID: str) -> None:
        """
        Login into an account with an SID

        **Parameters**
            - **SID** : SID of the account
        """
        self.__sid = SID

        self._profile = self.get_user_info(sid_to_uid(SID))
        self._profile.api_key = self.__api_key

        self.__update_public_key()
        headers.sid = self.__sid

        if self._socket_enabled:
            self.run_amino_socket()

    def verify_yourself(self, email: str, password: str) -> int:
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
            >>> client = Client()
            >>> client.verify_yourself("example@example.com", "password")
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
        response = self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )

        if response.status_code != 200:
            CheckException(response.text)

        return response.status_code

    def login(self, email: str, password: str) -> str:
        """
        Login into an account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
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
        response = self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )

        if response.status_code != 200:
            CheckException(response.text)

        body = loads(response.text)
        self.__sid = body["sid"]
        self._profile: UserProfile = UserProfile(
            body["account"]
        ).UserProfile
        self._profile.api_key = self.__api_key

        headers.sid = self.__sid
        headers.userId = self._profile.userId

        self.__update_public_key()
        if self._socket_enabled:
            self.run_amino_socket()

        return self.__sid

    def login_phone(self, phoneNumber: str, password: str) -> str:
        """
        Login into an account.

        **Parameters**
            - **phoneNumber** : Phone number of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
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

        response = self._session.post(
            url=f"{API_URL}/g/s/auth/login",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        self.run_amino_socket()
        if response.status_code != 200:
            CheckException(response.text)

        body = loads(response.text)
        self.__sid = body["sid"]
        self._profile: UserProfile = UserProfile(
            body["account"]
        ).UserProfile
        self._profile.api_key = self.__api_key

        headers.sid = self.__sid
        headers.userId = self._profile.userId

        self.__update_public_key()
        if self._socket_enabled:
            self.run_amino_socket()

        return self.__sid

    def restore(self, email: str, password: str) -> int:
        """
        Restore a deleted account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "secret": f"0 {password}",
            "deviceID": self.__device_id,
            "email": email,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/account/delete-request/cancel",
            headers=self._parse_headers(data=data),
            data=data, proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def logout(self) -> int:
        """
        Logout from an account.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "deviceID": self.__device_id,
            "clientType": 100,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/auth/logout",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)
        self.__sid = None
        headers.sid = None
        headers.userId = None

        if self._socket_enabled:
            self.close()

        return response.status_code

    def configure(self, age: int, gender: str) -> int:
        """
        Configure the settings of an account.

        **Parameters**
            - **age** : Age of the account. Minimum is 13.
            - **gender** : Gender of the account.
                - ``Male``, ``Female`` or ``Non-Binary``

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
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

        response = self._session.post(
            url=f"{API_URL}/g/s/persona/profile/basic",
            data=data,
            headers=self._parse_headers(data=data),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def verify(self, email: str, code: str) -> int:
        """
        Verify an account.

        **Parameters**
            - **email** : Email of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "validationContext": {
                "type": 1,
                "identity": email,
                "data": {"code": code}},
            "deviceID": self.__device_id,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/auth/check-security-validation",
            headers=self._parse_headers(data=data),
            data=data, proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def request_verify_code(
            self,
            email: str,
            resetPassword: bool = False,
            timeout: int = None
    ) -> int:
        """
        Request an verification code to the targeted email.

        **Parameters**
            - **email** : Email of the account.
            - **resetPassword** : If the code should be for Password Reset.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = {
            "identity": email,
            "type": 1,
            "deviceID": self.__device_id
        }

        if resetPassword:
            data["level"] = 2
            data["purpose"] = "reset-password"

        data = dumps(data)
        response = self._session.post(
            url=f"{API_URL}/g/s/auth/request-security-validation",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path,
            timeout=timeout
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def activate_account(self, email: str, code: str) -> int:
        """
        Activate an account.

        **Parameters**
            - **email** : Email of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = dumps({
            "type": 1,
            "identity": email,
            "data": {"code": code},
            "deviceID": self.__device_id
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/auth/activate-email",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_account(self, password: str) -> int:
        """
        Delete an account.

        **Parameters**
            - **password** : Password of the account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = dumps({
            "deviceID": self.__device_id,
            "secret": f"0 {password}"
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/account/delete-request",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def change_password(self, email: str, password: str, code: str) -> int:
        """
        Change password of an account.

        **Parameters**
            - **email** : Email of the account.
            - **password** : Password of the account.
            - **code** : Verification code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
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

        response = self._session.post(
            url=f"{API_URL}/g/s/auth/reset-password",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path)
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def check_device(self, deviceId: str) -> int:
        """
        Check if the Device ID is valid.

        **Parameters**
            - **deviceId** : ID of the Device.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "deviceID": deviceId,
            "bundleID": "com.narvii.amino.master",
            "clientType": 100,
            "timezone": -timezone // 1000,
            "systemPushEnabled": True,
            "locale": getdefaultlocale()[0],
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/device",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_account_info(self) -> UserProfile:
        """
        Get information about the account.

        **Returns**
            - **Success** : :meth:`UserProfile Object
                            <aminodorksfix.lib.util.objects.UserProfile>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/account",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfile(loads(response.text)["account"]).UserProfile

    def upload_media(self, file: BinaryIO, fileType: str) -> str:
        """
        Upload file to the amino servers.

        **Parameters**
            - **file** : File to be uploaded.

        **Returns**
            - **Success** : Url of the file uploaded to the server.

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        type_from_map = MEDIA_TYPES_MAP.get(fileType)
        if not type_from_map:
            raise SpecifyType(fileType)

        data = file.read()

        response = self._session.post(
            url=f"{API_URL}/g/s/media/upload",
            data=data,
            headers=headers.ApisHeaders(
                type=type_from_map,
                data=data,
                deviceId=self.__device_id
            ).headers,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["mediaValue"]

    def handle_socket_message(self, data) -> None:
        """
        Handle incoming socket messages.

        **Parameters**
            - **data** : The message received from the socket.

        **Returns**
            - The resolved data.
        """
        return self.resolve(data)

    def get_eventlog(self) -> Dict[str, Any]:
        """
        Get the event log of the account.

        **Returns**
            - **Success** : The event log of the account.

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/eventlog/profile?language=en",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def sub_clients(self, start: int = 0, size: int = 25) -> CommunityList:
        """
        List of Communities the account is in.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Community List
                            <aminodorksfix.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/community/joined" +
                f"?v=1&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityList(loads(
            response.text
        )["communityList"]).CommunityList

    def sub_clients_profile(
            self,
            start: int = 0,
            size: int = 25
    ) -> UserProfileList:
        response = self._session.get(
            url=f"{API_URL}/g/s/community/joined" +
                f"?v=1&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(
            loads(response.text)["userInfoInCommunities"]
        ).UserProfileList

    def get_user_info(self, userId: str) -> UserProfile:
        """
        Information of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`User Object
                            <aminodorksfix.lib.util.UserProfile>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfile(loads(response.text)["userProfile"]).UserProfile

    def get_community_info(self, comId: str) -> Community:
        """
        Information of an Community.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : :meth:`Community Object
                            <aminodorksfix.lib.util.Community>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s-x{comId}/community/info?" +
                "withInfluencerList=1&withTopicList=true" +
                "&influencerListOrderStrategy=fansCount",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return Community(loads(response.text)["community"]).Community

    def search_community(self, aminoId: str) -> CommunityList:
        """
        Search a Community byt its Amino ID.

        **Parameters**
            - **aminoId** : Amino ID of the Community.

        **Returns**
            - **Success** : :meth:`Community List
                             <aminodorksfix.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/search/amino-id-and-link?q={aminoId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        response = loads(response.text)["resultList"]
        if len(response) == 0:
            raise CommunityNotFound(aminoId)

        return CommunityList(
            [com["refObject"] for com in response]
        ).CommunityList

    def get_user_following(
            self,
            userId: str,
            start: int = 0,
            size: int = 25
    ) -> UserProfileList:
        """
        List of Users that the User is Following.

        **Parameters**
            - **userId** : ID of the User.
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User List
            <aminodorksfix.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}/joined?" +
                f"start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(
            loads(response.text)["userProfileList"]
        ).UserProfileList

    def get_user_followers(
            self,
            userId: str,
            start: int = 0,
            size: int = 25
    ) -> UserProfileList:
        """
        List of Users that are Following the User.

        **Parameters**
            - **userId** : ID of the User.
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User List
                            <aminodorksfix.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}/member?" +
                f"start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(
            loads(response.text)["userProfileList"]
        ).UserProfileList

    def get_blocked_users(
            self,
            start: int = 0,
            size: int = 25
    ) -> UserProfileList:
        """
        List of Users that the User Blocked.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Users List
                            <aminodorksfix.lib.util.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/block?start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(
            loads(response.text)["userProfileList"]
        ).UserProfileList

    def get_blocker_users(self, start: int = 0, size: int = 25) -> List[str]:
        """
        List of Users that are Blocking the User.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`List of User IDs <None>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/block/full-list?start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["blockerUidList"]

    def get_wall_comments(
            self,
            userId: str,
            sorting: str,
            start: int = 0,
            size: int = 25
    ) -> CommentList:
        """
        List of Wall Comments of an User.

        **Parameters**
            - **userId** : ID of the User.
            - **sorting** : Order of the Comments.
                - ``newest``, ``oldest``, ``top``
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Comments List
                            <aminodorksfix.lib.util.CommentList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        sorting_type = COMMENTS_SORTING_MAP.get(sorting)
        if not sorting_type:
            raise WrongType(sorting)

        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}/g-comment?" +
                f"sort={sorting_type}&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommentList(loads(response.text)["commentList"]).CommentList

    def flag(
            self,
            reason: str,
            flagType: int,
            userId: str,
            asGuest: bool = False
    ) -> int:
        """
        Flag a User.

        **Parameters**
            - **reason** : Reason of the Flag.
            - **flagType** : Type of the Flag.
            - **userId** : ID of the User.
            - *asGuest* : Execute as a Guest.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = dumps({
            "flagType": flagType,
            "message": reason,
            "objectId": userId,
            "objectType": 0,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/{"g-flag" if asGuest else "flag"}",
            data=data,
            headers=self._parse_headers(data=data),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def follow(self, userId: List[str] | str) -> int:
        """
        Follow an User or Multiple Users.

        **Parameters**
            - **userId** : ID of the User or List of IDs of the Users.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "targetUidList": userId, "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile/" +
                f"{self._profile.userId}/joined",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )

        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def unfollow(self, userId: str) -> int:
        """
        Unfollow an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{API_URL}/g/s/user-profile/" +
            f"{userId}/member/{self._profile.userId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def block(self, userId: str) -> int:
        """
        Block an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{API_URL}/g/s/block/{userId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def unblock(self, userId: str) -> int:
        """
        Unblock an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{API_URL}/g/s/block/{userId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def join_community(self, comId: str, invitationId: str = None) -> int:
        """
        Join a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **invitationId** : ID of the Invitation Code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data: Dict[str, str | int] = {"timestamp": int(timestamp() * 1000)}

        if invitationId:
            data["invitationId"] = invitationId

        dumped_data = dumps(data)
        response = self._session.post(
            url=f"{API_URL}/x{comId}/s/community/join",
            data=dumped_data,
            headers=self._parse_headers(data=dumped_data),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def request_join_community(self, comId: str, message: str = None) -> int:
        """
        Request to join a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **message** : Message to be sent.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "message": message,
            "timestamp": int(timestamp() * 1000)
        })
        response = self._session.post(
            url=f"{API_URL}/x{comId}/s/community/membership-request",
            data=data,
            headers=self._parse_headers(data=data),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def leave_community(self, comId: str) -> int:
        """
        Leave a Community.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{API_URL}/x{comId}/s/community/leave",
            headers=self._parse_headers(
                type="application/x-www-form-urlencoded"
            ),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def flag_community(
            self,
            comId: str,
            reason: str,
            flagType: int,
            isGuest: bool = False
    ) -> int:
        """
        Flag a Community.

        **Parameters**
            - **comId** : ID of the Community.
            - **reason** : Reason of the Flag.
            - **flagType** : Type of Flag.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "objectId": comId,
            "objectType": 16,
            "flagType": flagType,
            "message": reason,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/x{comId}/s/{"g-flag" if isGuest else "flag"}",
            data=data,
            headers=self._parse_headers(data=data),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def edit_profile(
            self,
            nickname: str = None,
            content: str = None,
            icon: BinaryIO = None,
            backgroundColor: str = None,
            backgroundImage: str = None,
            defaultBubbleId: str = None
    ) -> int:
        """
        Edit account's Profile.

        **Parameters**
            - **nickname** : Nickname of the Profile.
            - **content** : Biography of the Profile.
            - **icon** : Icon of the Profile.
            - **backgroundImage** : Url of the Background Picture
                                    of the Profile.
            - **backgroundColor** : Hexadecimal Background Color
                                    of the Profile.
            - **defaultBubbleId** : Chat bubble ID.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
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
            data["icon"] = self.upload_media(icon, "image")
        if content:
            data["content"] = content
        if backgroundColor:
            data["extensions"] = {"style": {
                "backgroundColor": backgroundColor
            }}
        if backgroundImage:
            data["extensions"] = {
                "style": {
                    "backgroundMediaList": [
                        [100, backgroundImage, None, None, None]
                    ]
                }
            }
        if defaultBubbleId:
            data["extensions"] = {"defaultBubbleId": defaultBubbleId}

        data = dumps(data)
        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile/{self._profile.userId}",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def set_amino_id(self, aminoId: str) -> int:
        """
        Edit account's Amino ID.

        **Parameters**
            - **aminoId** : Amino ID of the Account.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "aminoId": aminoId,
            "timestamp": int(timestamp() * 1000)
        })
        response = self._session.post(
            url=f"{API_URL}/g/s/account/change-amino-id",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_linked_communities(self, userId: str) -> CommunityList:
        """
        Get a List of Linked Communities of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`Community List
                            <aminodorksfix.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}/linked-community",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityList(
            loads(response.text)["linkedCommunityList"]
        ).CommunityList

    def get_unlinked_communities(self, userId: str) -> CommunityList:
        """
        Get a List of Unlinked Communities of an User.

        **Parameters**
            - **userId** : ID of the User.

        **Returns**
            - **Success** : :meth:`Community List
                            <aminodorksfix.lib.util.CommunityList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile/{userId}/linked-community",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityList(
            loads(response.text)["unlinkedCommunityList"]
        ).CommunityList

    def reorder_linked_communities(self, comIds: List[int]) -> int:
        """
        Reorder List of Linked Communities.

        **Parameters**
            - **comIds** : IDS of the Communities.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({"ndcIds": comIds, "timestamp": int(timestamp() * 1000)})
        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile/{self._profile.userId}" +
                "/linked-community/reorder",
            headers=self._parse_headers(data=data),
            data=data, proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def add_linked_community(self, comId: str) -> int:
        """
        Add a Linked Community on your profile.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile" +
                f"/{self._profile.userId}/linked-community/{comId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def remove_linked_community(self, comId: str) -> int:
        """
        Remove a Linked Community on your profile.

        **Parameters**
            - **comId** : ID of the Community.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{API_URL}/g/s/user-profile/" +
                f"{self._profile.userId}/linked-community/{comId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def comment(self, message: str, userId: str, replyTo: str = None) -> None:
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

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = {
            "content": message,
            "stickerId": None,
            "type": 0,
            "eventSource": "UserProfileView",
            "timestamp": int(timestamp() * 1000)
        }

        if replyTo:
            data["respondTo"] = replyTo

        data = dumps(data)

        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile/{userId}/g-comment",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

    def delete_comment(self, commentId: str, userId: str) -> None:
        """
        Delete a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)
            - **blogId** : ID of the Blog. (for Blogs)
            - **wikiId** : ID of the Wiki. (for Wikis)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{API_URL}/g/s/user-profile/{userId}/g-comment/{commentId}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

    def like_comment(self, commentId: str, userId: str) -> None:
        """
        Like a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)
            - **blogId** : ID of the Blog. (for Blogs)
            - **wikiId** : ID of the Wiki. (for Wikis)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "value": 4,
            "timestamp": int(timestamp() * 1000),
            "eventSource": "UserProfileView"
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/user-profile/{userId}" +
                f"/comment/{commentId}/g-vote?cv=1.2&value=1",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

    def unlike_comment(self, commentId: str, userId: str) -> None:
        """
        Remove a like from a Comment on a User's Wall, Blog or Wiki.

        **Parameters**
            - **commentId** : ID of the Comment.
            - **userId** : ID of the User. (for Walls)
            - **blogId** : ID of the Blog. (for Blogs)
            - **wikiId** : ID of the Wiki. (for Wikis)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{API_URL}/g/s/user-profile/{userId}/" +
            f"comment/{commentId}/g-vote?eventSource=UserProfileView",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

    def get_membership_info(self) -> Membership:
        """
        Get Information about your Amino+ Membership.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`Membership Object
                            <aminodorksfix.lib.util.Membership>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/membership?force=true",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return Membership(loads(response.text)).Membership

    def get_ta_announcements(
            self,
            language: str = "en",
            start: int = 0,
            size: int = 25
    ) -> BlogList:
        """
        Get the list of Team Amino's Announcement Blogs.

        **Parameters**
            - **language** : Language of the Blogs.
                - ``en``, ``es``, ``pt``, ``ar``, ``ru``, ``fr``, ``de``
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Blogs List
                            <aminodorksfix.lib.util.BlogList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        if language not in SUPPORTED_LANGAUGES:
            raise UnsupportedLanguage(language)

        response = self._session.get(
            url=f"{API_URL}/g/s/announcement?" +
                f"language={language}&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def get_wallet_info(self) -> WalletInfo:
        """
        Get Information about the account's Wallet.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`Wallet Object
                            <aminodorksfix.lib.util.WalletInfo>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/wallet",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WalletInfo(loads(response.text)["wallet"]).WalletInfo

    def get_wallet_history(
            self,
            start: int = 0,
            size: int = 25
    ) -> WalletHistory:
        """
        Get the Wallet's History Information.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Wallet Object
                            <aminodorksfix.lib.util.WalletInfo>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/wallet/coin/history?start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WalletHistory(
            loads(response.text)["coinHistoryList"]
        ).WalletHistory

    def get_from_deviceid(self, deviceId: str) -> str:
        """
        Get the User ID from an Device ID.

        **Parameters**
            - **deviceID** : ID of the Device.

        **Returns**
            - **Success** : :meth:`User ID
                            <aminodorksfix.lib.util.UserProfile.userId>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/auid?deviceId={deviceId}"
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["auid"]

    def get_from_code(self, code: str) -> FromCode:
        """
        Get the Object Information from the Amino URL Code.

        **Parameters**
            - **code** : Code from the Amino URL.
                - ``http://aminoapps.com/p/EXAMPLE``

        **Returns**
            - **Success** : :meth:`From Code Object
                            <aminodorksfix.lib.util.FromCode>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/link-resolution?q={code}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return FromCode(loads(response.text)["linkInfoV2"]).FromCode

    def get_from_id(
            self,
            objectId: str,
            objectType: int,
            comId: str = None
    ) -> FromCode:
        """
        Get the Object Information from the Object ID and Type.

        **Parameters**
            - **objectID** : ID of the Object. User ID, Blog ID, etc.
            - **objectType** : Type of the Object.
            - *comId* : ID of the Community. Use if the Object is
                                                    in a Community.

        **Returns**
            - **Success** : :meth:`From Code Object
                            <aminodorksfix.lib.util.FromCode>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({
            "objectId": objectId,
            "targetCode": 1,
            "objectType": objectType,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/{f"s-x{comId}" if comId else "s"}" +
                "/link-resolution",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return FromCode(loads(response.text)["linkInfoV2"]).FromCode

    def get_supported_languages(self) -> List[str]:
        """
        Get the List of Supported Languages by Amino.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : :meth:`List of Supported Languages <List>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/community-collection/" +
                "supported-languages?start=0&size=100",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["supportedLanguages"]

    def claim_new_user_coupon(self) -> int:
        """
        Claim the New User Coupon available when a new account is created.

        **Parameters**
            - No parameters required.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{API_URL}/g/s/coupon/new-user-coupon/claim",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_subscriptions(
            self,
            start: int = 0,
            size: int = 25
    ) -> List[List[Any]]:
        """
        Get Information about the account's Subscriptions.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`List <List>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/store/subscription?" +
                f"objectType=122&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["storeSubscriptionItemList"]

    def get_all_users(
            self,
            type: str = "recent",
            start: int = 0,
            size: int = 25
    ) -> UserProfileCountList:
        """
        Get list of users of Amino.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`User Profile Count List Object
                            <aminodorksfix.lib.util.UserProfileCountList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/g/s/user-profile?" +
                f"type={type}&start={start}&size={size}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileCountList(loads(response.text)).UserProfileCountList

    def link_identify(self, code: str) -> Any:
        """
        Identifies a community link.

        **Parameters**
            - *code* : The invite code of the community.

        **Returns**
            - **Success** : The identified community object

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            f"{API_URL}/g/s/community/link-identify" +
            f"?q=http%3A%2F%2Faminoapps.com%2Finvite%2F{code}",
            headers=self._parse_headers(),
            proxies=self.__proxies,
            verify=self.__certificate_path
        )

        return loads(response.text)

    def wallet_config(self, level: int) -> int:
        """
        Changes ads config

        **Parameters**
            - **level** - Level of the ads.
                - ``1``, ``2``

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = dumps({
            "adsLevel": level,
            "timestamp": int(timestamp() * 1000)
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/wallet/ads/config",
            headers=self._parse_headers(data=data),
            data=data,
            proxies=self.__proxies,
            verify=self.__certificate_path
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def purchase(self, objectId: str, isAutoRenew: bool = False) -> int:
        data = dumps({
            "objectId": objectId,
            "objectType": 114,
            "v": 1,
            "paymentContext":
                {
                    "discountStatus": 0,
                    "isAutoRenew": isAutoRenew
                },
            "timestamp": timestamp()
        })

        response = self._session.post(
            url=f"{API_URL}/g/s/store/purchase",
            headers=self._parse_headers(data=data), data=data
        )
        if response.status_code != 200:
            return CheckException(loads(response.text))

        return response.status_code
