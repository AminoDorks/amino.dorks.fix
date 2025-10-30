from json import (
    dumps,
    loads
)
from typing import (
    Any,
    Dict,
    BinaryIO
)
from asyncio import (
    get_event_loop,
    new_event_loop
)

from ..lib.util.objects import (
    UserProfile,
    CommunityList,
    JoinRequest,
    CommunityStats,
    UserProfileList,
    NoticeList
)
from ..lib.util.exceptions import (
    CheckException,
    CommunityNeeded,
    WrongType
)
from ..constants import (
    API_URL,
    ACM_MODULES_MAP
)

from time import time as timestamp

from .client import Client

class ACM(Client):
    def __init__(self, profile: UserProfile, comId: str = None) -> None:
        Client.__init__(self, api_key=profile.api_key)
        self.comId = comId

    def __del__(self):
        try:
            loop = get_event_loop()
            loop.create_task(self._close_session())
        except RuntimeError:
            loop = new_event_loop()
            loop.run_until_complete(self._close_session())

    async def _close_session(self) -> None:
        if not self._session.closed:
            await self._session.close()

    async def create_community(
            self,
            name: str,
            tagline: str,
            icon: BinaryIO,
            themeColor: str,
            joinType: int = 0,
            primaryLanguage: str = "en"
    ) -> int:
        data = dumps({
            "icon": {
                "height": 512.0,
                "imageMatrix": [1.6875, 0.0, 108.0, 0.0, 1.6875, 497.0, 0.0, 0.0, 1.0],
                "path": await self.upload_media(icon, "image"),
                "width": 512.0,
                "x": 0.0,
                "y": 0.0
            },
            "joinType": joinType,
            "name": name,
            "primaryLanguage": primaryLanguage,
            "tagline": tagline,
            "templateId": 9,
            "themeColor": themeColor,
            "timestamp": int(timestamp() * 1000)
        })

        async with self._session.post(
            url=f"{API_URL}/g/s/community",
            headers=await self._parse_headers(data=data),
            data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())
            
            return response.status

    async def delete_community(
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
            "deviceID": self.device_id
        })

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(
            url=f"{API_URL}/g/s-x{self.comId}/community/delete-request",
            headers=await self._parse_headers(data=data),
            data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def list_communities(self, start: int = 0, size: int = 25) -> CommunityList:
        async with self._session.get(
            url=f"{API_URL}/g/s/community/managed?start={start}&size={size}",
            headers=await self._parse_headers()
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())
            
            return CommunityList(loads(await response.text())["communityList"]).CommunityList

    async def get_categories(self, start: int = 0, size: int = 25) -> Dict[str, Any]:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.get(
            url=f"{API_URL}/x{self.comId}/s/blog-category?start={start}&size={size}",
            headers=await self._parse_headers()
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())

    async def change_sidepanel_color(self, color: str) -> Dict[str, Any]:
        data = dumps({
            "path": "appearance.leftSidePanel.style.iconColor",
            "value": color,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(
            url=f"{API_URL}/x{self.comId}/s/community/configuration",
            headers=await self._parse_headers(data=data),
            data=data
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return loads(await response.text())

    async def promote(self, userId: str, rank: str) -> int:
        rank = rank.lower().replace("agent", "transfer-agent")

        if rank.lower() not in ["transfer-agent", "leader", "curator"]:
            raise WrongType(rank)

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/user-profile/{userId}/{rank}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_join_requests(self, start: int = 0, size: int = 25) -> JoinRequest:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.get(url=f"{API_URL}/x{self.comId}/s/community/membership-request?status=pending&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return JoinRequest(loads(await response.text())).JoinRequest

    async def accept_join_request(self, userId: str) -> int:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/membership-request/{userId}/approve", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def reject_join_request(self, userId: str) -> int:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/membership-request/{userId}/reject", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_community_stats(self) -> CommunityStats:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.get(url=f"{API_URL}/x{self.comId}/s/community/stats", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return CommunityStats(loads(await response.text())["communityStats"]).CommunityStats

    async def get_community_user_stats(self, type: str, start: int = 0, size: int = 25) -> UserProfileList:
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.get(
            url=f"{API_URL}/x{self.comId}/s/community/stats/moderation?type={type}&start={start}&size={size}",
            headers=await self._parse_headers()
        ) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return UserProfileList(loads(await response.text())["userProfileList"]).UserProfileList

    async def change_welcome_message(self, message: str, isEnabled: bool = True) -> int:
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

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/configuration", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def change_guidelines(self, message: str):
        data = dumps({
            "content": message,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/guideline", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def edit_community(
            self,
            name: str = None,
            description: str = None,
            aminoId: str = None,
            primaryLanguage: str = None,
            themePackUrl: str = None
    ) -> int:
        data: Dict[str, Any] = {"timestamp": int(timestamp() * 1000)}

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

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/settings", headers=await self._parse_headers(data=dumped_data), data=dumped_data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def change_module(self, module: str, isEnabled: bool):
        data = dumps({
            "path": ACM_MODULES_MAP.get(module, 'chat'),
            "value": isEnabled,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/community/configuration", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def add_influencer(self, userId: str, monthlyFee: int):
        data = dumps({
            "monthlyFee": monthlyFee,
            "timestamp": int(timestamp() * 1000)
        })

        if not self.comId:
            raise CommunityNeeded()

        async with self._session.post(url=f"{API_URL}/x{self.comId}/s/influencer/{userId}", headers=await self._parse_headers(data=data), data=data) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def remove_influencer(self, userId: str):
        if not self.comId:
            raise CommunityNeeded()
        async with self._session.delete(url=f"{API_URL}/x{self.comId}/s/influencer/{userId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status

    async def get_notice_list(self, start: int = 0, size: int = 25):
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.get(url=f"{API_URL}/x{self.comId}/s/notice?type=management&status=1&start={start}&size={size}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return NoticeList(loads(await response.text())["noticeList"]).NoticeList

    async def delete_pending_role(self, noticeId: str):
        if not self.comId:
            raise CommunityNeeded()

        async with self._session.delete(url=f"{API_URL}/x{self.comId}/s/notice/{noticeId}", headers=await self._parse_headers()) as response:
            if response.status != 200:
                return CheckException(await response.text())

            return response.status
