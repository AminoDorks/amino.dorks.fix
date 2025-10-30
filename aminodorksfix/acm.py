from json import (
    dumps,
    loads
)
from typing import (
    Any,
    Dict
)

from .lib.util.objects import (
    UserProfile,
    CommunityList,
    JoinRequest,
    CommunityStats,
    UserProfileList,
    NoticeList
)
from .lib.util.exceptions import (
    CheckException,
    CommunityNeeded,
    WrongType
)
from .constants import (
    API_URL,
    ACM_MODULES_MAP
)

from time import time as timestamp

from .client import Client
from .lib.util import headers

device = headers.device_id


class ACM(Client):
    def __init__(self, profile: UserProfile, comId: str = None):
        Client.__init__(self, api_key=profile.api_key)
        self.comId = comId

    def delete_community(
            self,
            email: str,
            password: str,
            verificationCode: str
    ) -> int:
        data = dumps({
            "secret": f"0 {password}",
            "validationContext": {
                "data": {
                    "code": verificationCode
                },
                "type": 1,
                "identity": email
            },
            "deviceID": device
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/g/s-x{self.comId}/community/delete-request",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def list_communities(
            self,
            start: int = 0,
            size: int = 25
    ) -> CommunityList:
        response = self._session.get(
            url=f"{API_URL}/g/s/community/managed?start={start}&size={size}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityList(
            loads(response.text)["communityList"]
        ).CommunityList

    def get_categories(self, start: int = 0, size: int = 25) -> Dict[str, Any]:
        if not self.comId:
            raise CommunityNeeded()
        response = self._session.get(
            url=f"{API_URL}/x{self.comId}/s/blog-category?" +
                f"start={start}&size={size}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def change_sidepanel_color(self, color: str) -> Dict[str, Any]:
        data = dumps({
            "path": "appearance.leftSidePanel.style.iconColor",
            "value": color,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/configuration",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def promote(self, userId: str, rank: str) -> int:
        rank = rank.lower().replace("agent", "transfer-agent")

        if rank.lower() not in ["transfer-agent", "leader", "curator"]:
            raise WrongType(rank)

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/" +
            f"s/user-profile/{userId}/{rank}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_join_requests(self, start: int = 0, size: int = 25) -> JoinRequest:
        if not self.comId:
            raise CommunityNeeded()

        response = self._session.get(
            url=f"{API_URL}/x{self.comId}/s/community/membership" +
            f"-request?status=pending&start={start}&size={size}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return JoinRequest(loads(response.text)).JoinRequest

    def accept_join_request(self, userId: str) -> int:
        data = dumps({})

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/membership-request" +
                f"/{userId}/accept",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def reject_join_request(self, userId: str) -> int:
        data = dumps({})

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/membership-request" +
                f"/{userId}/reject",
                headers=self._parse_headers(data=data),
                data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_community_stats(self) -> CommunityStats:
        if not self.comId:
            raise CommunityNeeded()

        response = self._session.get(
            url=f"{API_URL}/x{self.comId}/s/community/stats",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityStats(
            loads(response.text)["communityStats"]
        ).CommunityStats

    def get_community_user_stats(
            self,
            type: str,
            start: int = 0,
            size: int = 25
    ) -> UserProfileList:
        if not self.comId:
            raise CommunityNeeded()

        response = self._session.get(
            url=f"{API_URL}/x{self.comId}/s/community/stats/moderation?" +
                f"type={type.lower()}&start={start}&size={size}",
                headers=self._parse_headers()
            )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(
            loads(response.text)["userProfileList"]
        ).UserProfileList

    def change_welcome_message(
            self,
            message: str,
            isEnabled: bool = True
    ) -> int:
        data = dumps({
            "path": "general.welcomeMessage",
            "value": {
                "enabled": isEnabled,
                "text": message
            },
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/configuration",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def change_guidelines(self, message: str) -> int:
        data = dumps({
            "content": message,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/guideline",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def edit_community(
            self,
            name: str = None,
            description: str = None,
            aminoId: str = None,
            primaryLanguage: str = None,
            themePackUrl: str = None
    ) -> int:
        data: Dict[str, str | int] = {"timestamp": int(timestamp() * 1000)}

        if name:
            data["name"] = name
        if description:
            data["content"] = description
        if aminoId:
            data["endpoint"] = aminoId
        if primaryLanguage:
            data["primaryLanguage"] = primaryLanguage
        if themePackUrl:
            data["themePackUrl"] = themePackUrl

        dumped_data = dumps(data)

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            f"{API_URL}/x{self.comId}/s/community/settings",
            data=dumped_data,
            headers=self._parse_headers(data=dumped_data)
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def change_module(self, module: str, isEnabled: bool) -> int:
        data = dumps({
            "path": ACM_MODULES_MAP.get(module, 'chat'),
            "value": isEnabled,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/configuration",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def add_influencer(self, userId: str, monthlyFee: int) -> int:
        data = dumps({
            "monthlyFee": monthlyFee,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()
        response = self._session.post(
            url=f"{API_URL}/x{self.comId}/s/influencer/{userId}",
            headers=self._parse_headers(data=data),
            data=data
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def remove_influencer(self, userId: str) -> int:
        if not self.comId:
            raise CommunityNeeded()
        response = self._session.delete(
            url=f"{API_URL}/x{self.comId}/s/influencer/{userId}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_notice_list(self, start: int = 0, size: int = 25) -> NoticeList:
        if not self.comId:
            raise CommunityNeeded()
        response = self._session.get(
            url=f"{API_URL}/x{self.comId}/s/notice?type=management" +
                f"&status=1&start={start}&size={size}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return NoticeList(loads(response.text)["noticeList"]).NoticeList

    def delete_pending_role(self, noticeId: str) -> int:
        if not self.comId:
            raise CommunityNeeded()
        response = self._session.delete(
            url=f"{API_URL}/x{self.comId}/s/notice/{noticeId}",
            headers=self._parse_headers()
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code
