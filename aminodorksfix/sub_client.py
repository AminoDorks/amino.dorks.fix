from base64 import b64encode
from binascii import hexlify
from json import dumps, loads
from os import urandom
from time import time as timestamp
from time import timezone
from typing import Any, BinaryIO, Dict, List, Unpack
from uuid import UUID
from requests import Session

from json_minify import json_minify

from .client import Client
from .constants import (
    API_URL,
    COMMENTS_SORTING_MAP,
    FEATURE_CHAT_TIME_MAP,
    FEATURE_ITEMS_TIME_MAP,
)
from .lib.util import headers
from .lib.util.enums import LeaderboardType
from .lib.util.exceptions import CheckException, NoCommunity, SpecifyType, WrongType
from .lib.util.helpers import gen_deviceId
from .lib.util.models import SubClientKwargs
from .lib.util.objects import (
    AdminLogList,
    BlogCategoryList,
    BlogList,
    CommentList,
    CommunityStickerCollection,
    GetBlogInfo,
    GetMessages,
    GetSharedFolderInfo,
    GetWikiInfo,
    InfluencerFans,
    InviteCode,
    InviteCodeList,
    LiveLayer,
    LotteryLog,
    Message,
    MessageList,
    NoticeList,
    NotificationList,
    QuizQuestionList,
    QuizRankings,
    RecentBlogs,
    SharedFolderFile,
    SharedFolderFileList,
    StickerCollection,
    Thread,
    ThreadList,
    TippedUsersSummary,
    UserAchievements,
    UserCheckIns,
    UserProfile,
    UserProfileCountList,
    UserProfileList,
    UserSavedBlogs,
    VcReputation,
    WikiCategory,
    WikiCategoryList,
    WikiList,
    WikiRequestList,
)

device = headers.device_id
headers.sid = headers.sid


class SubClient(Client):
    __slots__ = (
        "__comId",
        "__endpoint",
        "__cross_point",
        "__profile",
        "__vc_connect",
        "_community",
    )

    def __init__(
        self, comId: str = None, aminoId: str = None, **kwargs: Unpack[SubClientKwargs]
    ) -> None:
        """
        Initialize a SubClient object.

        Parameters:
        comId (str): The community ID.
        aminoId (str): The Amino ID.
        **kwargs: Unpack[SubClientKwargs]

        Raises:
        NoCommunity: If neither comId or aminoId is provided.
        """
        if not (comId or aminoId):
            raise NoCommunity()

        Client.__init__(
            self,
            api_key=kwargs.get("profile").api_key,
            deviceId=kwargs.get("device_id", gen_deviceId()),
            proxies=kwargs.get("proxies"),
            certificatePath=kwargs.get("certificate_path", False),
        )

        if comId:
            self.__comId = comId
            self._community = self.get_community_info(comId)

        if aminoId:
            self.__comId = self.get_from_code(f"http://aminoapps.com/c/{aminoId}").comId
            self._community = self.get_community_info(str(self.__comId))

        self.__endpoint = f"{API_URL}/x{self.__comId}"
        self.__cross_point = f"{API_URL}/g/s-x{self.__comId}"
        self.__profile = kwargs.get("profile")
        self.vc_connect = False
    
    @property
    def profile(self) -> UserProfile:
        return self.__profile
    
    @property
    def session(self) -> Session:
        return self.session

    def get_invite_codes(
        self, status: str = "normal", start: int = 0, size: int = 25
    ) -> InviteCodeList:
        """
        Get a list of invitation codes of the community.

        **Parameters**
            - **status** : Status of the invitation code.
            - **start** : Where to start the list.
            - **size** : Size of the list.

        **Returns**
            - **Success** : :meth:`InviteCode List`
                              <aminodorksfix.lib.util.InviteCodeList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{self.__cross_point}/community/invitation"
            + f"?status={status}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return InviteCodeList(
            loads(response.text)["communityInvitationList"]
        ).InviteCodeList

    def generate_invite_code(self, duration: int = 0, force: bool = True) -> InviteCode:
        """
        Generate an invitation code for the community.

        **Parameters**
            - **duration** : Duration of the invitation code.
            - **force** : Whether to force generate the invitation code.

        **Returns**
            - **Success** : The generated invitation code.

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps(
            {"duration": duration, "force": force, "timestamp": int(timestamp() * 1000)}
        )

        response = self._session.post(
            url=f"{self.__cross_point}/community/invitation",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return InviteCode(loads(response.text)["communityInvitation"]).InviteCode

    def get_vip_users(self) -> UserProfileList:
        """
        Get a list of VIP users of the community.

        **Returns**
            - **Success** : :meth:`UserProfileList
                            <aminodorksfix.lib.util.objects.UserProfileList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{API_URL}/{self.__comId}/s/influencer",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def delete_invite_code(self, inviteId: str) -> int:
        """
        Delete an Invitation Code of the Community.

        **Parameters**
            - **inviteId** : ID of the Invitation Code.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{self.__cross_point}/community/invitation/{inviteId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def post_blog(
        self,
        title: str,
        content: str,
        imageList: List[BinaryIO] = [],
        captionList: List[str] = [],
        categoriesList: list = None,
        backgroundColor: str = None,
        fansOnly: bool = False,
        extensions: dict = None,
        crash: bool = False,
    ) -> int:
        """
        Post a blog to the Community.

        **Parameters**
            - **title** : Title of the blog.
            - **content** : Content of the blog.
            - **imageList** : List of images to be uploaded for the blog.
            - **captionList** : List of captions for the images.
            - **categoriesList** : List of categories for the blog.
            - **backgroundColor** : Background color of the blog.
            - **fansOnly** : If the blog should be Fans Only or not.
            - **extensions** : Additional blog extensions.
            - **crash** : If the function should intentionally crash or not.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        mediaList = []

        for image, caption in zip(imageList, captionList):
            mediaList.append([100, self.upload_media(image, "image"), caption])

        data = {
            "address": None,
            "content": content,
            "title": title,
            "mediaList": mediaList,
            "extensions": extensions,
            "latitude": 0,
            "longitude": 0,
            "eventSource": "GlobalComposeMenu",
            "timestamp": int(timestamp() * 1000),
        }

        if fansOnly:
            data["extensions"] = {"fansOnly": fansOnly}
        if backgroundColor:
            data["extensions"] = {"style": {"backgroundColor": backgroundColor}}
        if categoriesList:
            data["taggedBlogCategoryIdList"] = categoriesList

        data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def post_wiki(
        self,
        title: str,
        content: str,
        icon: str = None,
        imageList: List[BinaryIO] = [],
        keywords: str = None,
        backgroundColor: str = None,
        fansOnly: bool = False,
    ) -> int:
        """
        Post a Wiki to the Community.

        **Parameters**
            - **title** : Title of the Wiki.
            - **content** : Content of the Wiki.
            - **icon** : Icon of the Wiki.
            - **imageList** : List of images to be uploaded for the Wiki.
            - **keywords** : Keywords of the Wiki.
            - **backgroundColor** : Background color of the Wiki.
            - **fansOnly** : If the Wiki should be Fans Only or not.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        mediaList = []

        for image in imageList:
            mediaList.append([100, self.upload_media(image, "image"), None])

        data = {
            "label": title,
            "content": content,
            "mediaList": mediaList,
            "eventSource": "GlobalComposeMenu",
            "timestamp": int(timestamp() * 1000),
        }

        if icon:
            data["icon"] = icon
        if keywords:
            data["keywords"] = keywords
        if fansOnly:
            data["extensions"] = {"fansOnly": fansOnly}
        if backgroundColor:
            data["extensions"] = {"style": {"backgroundColor": backgroundColor}}
        data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/item",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def edit_blog(
        self,
        blogId: str,
        title: str = None,
        content: str = None,
        imageList: List[BinaryIO] = [],
        categoriesList: list = None,
        backgroundColor: str = None,
        fansOnly: bool = False,
    ) -> int:
        """
        Edit a Blog.

        **Parameters**
            - **blogId** : ID of the Blog.
            - **title** : Title of the Blog.
            - **content** : Content of the Blog.
            - **imageList** : List of images to be uploaded for the Blog.
            - **categoriesList** : List of categories for the Blog.
            - **backgroundColor** : Background color of the Blog.
            - **fansOnly** : If the Blog should be Fans Only or not.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        mediaList = []

        for image in imageList:
            mediaList.append([100, self.upload_media(image, "image"), None])

        data = {
            "address": None,
            "mediaList": mediaList,
            "latitude": 0,
            "longitude": 0,
            "eventSource": "PostDetailView",
            "timestamp": int(timestamp() * 1000),
        }

        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if fansOnly:
            data["extensions"] = {"fansOnly": fansOnly}
        if backgroundColor:
            data["extensions"] = {"style": {"backgroundColor": backgroundColor}}
        if categoriesList:
            data["taggedBlogCategoryIdList"] = categoriesList
        data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{blogId}",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_blog(self, blogId: str) -> int:
        """
        Delete a Blog.

        **Parameters**
            - **blogId** : ID of the Blog.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{self.__endpoint}/s/blog/{blogId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_wiki(self, wikiId: str) -> int:
        """
        Delete a Wiki.

        **Parameters**
            - **wikiId** : ID of the Wiki.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{self.__endpoint}/s/item/{wikiId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def repost_blog(
        self, content: str = None, blogId: str = None, wikiId: str = None
    ) -> int:
        """
        Repost a Blog or a Wiki.

        **Parameters**
            - **content** : Content of the Repost.
            - **blogId** : ID of the Blog.
            - **wikiId** : ID of the Wiki.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps(
            {
                "content": content,
                "refObjectId": blogId if blogId else wikiId,
                "refObjectType": 1 if blogId else 2,
                "type": 2,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def check_in(self, timezone: int = -timezone // 1000) -> int:
        """
        Check-in to the Community.

        **Parameters**
            - **timezone** : Timezone of the User.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({"timezone": timezone, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/check-in",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def repair_check_in(self, method: int = 0) -> int:
        """
        Repair Check-in to the Community.

        **Parameters**
            - **method** : Method of Check-in Repair.
                - 0 : Coins
                - 1 : Amino+

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps(
            {
                "timestamp": int(timestamp() * 1000),
                "repairMethod": "1" if method == 0 else "2",
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/check-in/repair",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def lottery(self, tz: int = -timezone // 1000) -> LotteryLog:
        """
        Get the Lottery Log of the User.

        **Parameters**
            - **tz** : Timezone of the User.

        **Returns**
            - **LotteryLog** : Lottery Log of the User

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({"timezone": tz, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/check-in/lottery",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return LotteryLog(loads(response.text)["lotteryLog"]).LotteryLog

    def edit_profile(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        nickname: str = None,
        content: str = None,
        icon: BinaryIO = None,
        chatRequestPrivilege: str = None,
        imageList: List[BinaryIO] = [],
        captionList: List[str] = [],
        backgroundImage: str = None,
        backgroundColor: str = None,
        titles: List[str] = None,
        colors: List[str] = None,
        defaultBubbleId: str = None,
    ) -> int:
        """
        Edit the Profile of the User.

        **Parameters**
            - **nickname** : Nickname of the Profile.
            - **content** : Biography of the Profile.
            - **icon** : Icon of the Profile.
            - **chatRequestPrivilege** : Privilege of the Chat Invite Request.
            - **imageList** : List of Images to be uploaded to the Profile.
            - **captionList** : List of Captions corresponding to the Images.
            - **backgroundImage** : Url of the Background Picture
                                                    of the Profile.
            - **backgroundColor** : Hexadecimal Background Color
                                                    of the Profile.
            - **titles** : List of Titles Texts.
            - **colors** : List of Hexadecimal Colors corresponding
                                                    to the Title Texts.
            - **defaultBubbleId** : Chat bubble ID.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        mediaList: List[List[str | int]] = []

        data: Dict[str, Any] = {"timestamp": int(timestamp() * 1000)}

        for image, caption in zip(imageList, captionList):
            mediaList.append([100, self.upload_media(image, "image"), caption])

        if len(mediaList):
            data["mediaList"] = mediaList

        if nickname:
            data["nickname"] = nickname
        if icon:
            data["icon"] = self.upload_media(icon, "image")
        if content:
            data["content"] = content

        if chatRequestPrivilege:
            data["extensions"] = {"privilegeOfChatInviteRequest": chatRequestPrivilege}
        if backgroundImage:
            data["extensions"] = {
                "style": {
                    "backgroundMediaList": [[100, backgroundImage, None, None, None]]
                }
            }
        if backgroundColor:
            data["extensions"] = {"style": {"backgroundColor": backgroundColor}}
        if defaultBubbleId:
            data["extensions"] = {"defaultBubbleId": defaultBubbleId}

        if titles and colors:
            custom_titles = []
            for title, color in zip(titles, colors):
                custom_titles.append({"title": title, "color": color})

            data["extensions"] = {"customTitles": custom_titles}

        dumped_data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/{self.profile.userId}",
            headers=self.parse_headers(data=dumped_data),
            data=dumped_data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def vote_poll(self, blogId: str, optionId: str) -> int:
        data = dumps(
            {
                "value": 1,
                "eventSource": "PostDetailView",
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{blogId}" + f"/poll/option/{optionId}/vote",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def comment(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        message: str,
        userId: str = None,
        blogId: str = None,
        wikiId: str = None,
        replyTo: str = None,
        isGuest: bool = False,
    ) -> None:
        data = {
            "content": message,
            "stickerId": None,
            "type": 0,
            "timestamp": int(timestamp() * 1000),
        }

        if replyTo:
            data["respondTo"] = replyTo

        if userId:
            data["eventSource"] = "UserProfileView"
            data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile"
                + f"/{userId}/{'g-comment' if isGuest else 'comment'}",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

        elif blogId:
            data["eventSource"] = "PostDetailView"
            data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/blog"
                + f"/{blogId}/{'g-comment' if isGuest else 'comment'}",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

        elif wikiId:
            data["eventSource"] = "PostDetailView"
            data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}"
                + f"/{'g-comment' if isGuest else 'comment'}",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def delete_comment(
        self, commentId: str, userId: str = None, blogId: str = None, wikiId: str = None
    ) -> None:
        if userId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/user-profile"
                + f"/{userId}/comment/{commentId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
        elif blogId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/blog/{blogId}/comment/{commentId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
        elif wikiId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/item/{wikiId}/comment/{commentId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def like_blog(self, blogId: List[str] | str = None, wikiId: str = None) -> None:
        """
        Like a Blog, Multiple Blogs or a Wiki.

        **Parameters**
            - **blogId** : ID of the Blog or List of IDs of the Blogs.
                                                         (for Blogs)
            - **wikiId** : ID of the Wiki. (for Wikis)

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data: Dict[str, str | int | List[str]] = {
            "value": 4,
            "timestamp": int(timestamp() * 1000),
        }

        if blogId:
            if isinstance(blogId, str):
                data["eventSource"] = "UserProfileView"
                dumped_blog_data = dumps(data)

                response = self._session.post(
                    url=f"{self.__endpoint}/s/blog/{blogId}/vote?cv=1.2",
                    headers=self.parse_headers(data=dumped_blog_data),
                    data=dumped_blog_data,
                    proxies=getattr(self, "_Client__proxies"),
                    verify=getattr(self, "_Client__certificate_path", None),
                )
                if response.status_code != 200:
                    return CheckException(response.text)

            elif isinstance(blogId, list):
                data["targetIdList"] = blogId
                dumped_multiple_data = dumps(data)

                response = self._session.post(
                    url=f"{self.__endpoint}/s/feed/vote",
                    headers=self.parse_headers(data=dumped_multiple_data),
                    data=dumped_multiple_data,
                    proxies=getattr(self, "_Client__proxies"),
                    verify=getattr(self, "_Client__certificate_path", None),
                )
                if response.status_code != 200:
                    return CheckException(response.text)

        elif wikiId:
            data["eventSource"] = "PostDetailView"
            dumped_wiki_data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}/vote?cv=1.2",
                headers=self.parse_headers(data=dumped_wiki_data),
                data=dumped_wiki_data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def unlike_blog(self, blogId: str = None, wikiId: str = None) -> None:
        if blogId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/blog/{blogId}"
                + "/vote?eventSource=UserProfileView",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
        elif wikiId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/item/{wikiId}"
                + "/vote?eventSource=PostDetailView",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def like_comment(
        self, commentId: str, userId: str = None, blogId: str = None, wikiId: str = None
    ) -> None:
        data: Dict[str, str | int] = {"value": 1, "timestamp": int(timestamp() * 1000)}

        if userId:
            data["eventSource"] = "UserProfileView"
            dumped_user_data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile/"
                + f"{userId}/comment/{commentId}/vote?cv=1.2&value=1",
                headers=self.parse_headers(data=dumped_user_data),
                data=dumped_user_data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

        elif blogId:
            data["eventSource"] = "PostDetailView"
            dumped_blog_data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{blogId}"
                + f"/comment/{commentId}/vote?cv=1.2&value=1",
                headers=self.parse_headers(data=dumped_blog_data),
                data=dumped_blog_data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

        elif wikiId:
            data["eventSource"] = "PostDetailView"
            dumped_wiki_data = dumps(data)

            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}"
                + f"/comment/{commentId}/g-vote?cv=1.2&value=1",
                headers=self.parse_headers(data=dumped_wiki_data),
                data=dumped_wiki_data,
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def unlike_comment(
        self, commentId: str, userId: str = None, blogId: str = None, wikiId: str = None
    ) -> None:
        if userId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/user-profile"
                + f"/{userId}/comment/{commentId}/"
                + "g-vote?eventSource=UserProfileView",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
        elif blogId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/blog/"
                + f"{blogId}/comment/{commentId}"
                + "/g-vote?eventSource=PostDetailView",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
        elif wikiId:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/item/"
                + f"{wikiId}/comment/{commentId}"
                + "/g-vote?eventSource=PostDetailView",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

    def upvote_comment(self, blogId: str, commentId: str) -> int:
        data = dumps(
            {
                "value": 1,
                "eventSource": "PostDetailView",
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{blogId}"
            + f"/comment/{commentId}/vote?cv=1.2&value=1",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def downvote_comment(self, blogId: str, commentId: str) -> int:
        data = dumps(
            {
                "value": -1,
                "eventSource": "PostDetailView",
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{blogId}"
            + f"/comment/{commentId}/vote?cv=1.2&value=-1",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def unvote_comment(self, blogId: str, commentId: str) -> int:
        response = self._session.delete(
            url=f"{self.__endpoint}/s/blog/"
            + f"{blogId}/comment/{commentId}/"
            + "vote?eventSource=PostDetailView",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def reply_wall(self, userId: str, commentId: str, message: str) -> int:
        data = dumps(
            {
                "content": message,
                "stackedId": None,
                "respondTo": commentId,
                "type": 0,
                "eventSource": "UserProfileView",
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/{userId}/comment",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def send_active_obj(
        self,
        startTime: int = None,
        endTime: int = None,
        optInAdsFlags: int = 2147483647,
        timezone: int = -timezone // 1000,
        timers: List[Dict[int, int]] = None,
        timestamp: int = int(timestamp() * 1000),
    ) -> int:
        data = {
            "userActiveTimeChunkList": [{"start": startTime, "end": endTime}],
            "timestamp": timestamp,
            "optInAdsFlags": optInAdsFlags,
            "timezone": timezone,
        }
        if timers:
            data["userActiveTimeChunkList"] = timers
        data = json_minify(dumps(data))

        response = self._session.post(
            url=f"{self.__endpoint}/s/community/stats/user-active-time",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def activity_status(self, status: str) -> int:
        data = dumps(
            {
                "onlineStatus": 1 if status == "on" else 0,
                "duration": 86400,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/"
            + f"{self._profile.userId}/online-status",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def check_notifications(self) -> int:
        response = self._session.post(
            url=f"{self.__endpoint}/s/notification/checked",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_notification(self, notificationId: str) -> int:
        response = self._session.delete(
            url=f"{self.__endpoint}/s/notification/{notificationId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def clear_notifications(self) -> int:
        response = self._session.delete(
            url=f"{self.__endpoint}/s/notification",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def start_chat(
        self,
        userId: List[str] | str,
        message: str,
        title: str = None,
        content: str = None,
        isGlobal: bool = False,
        publishToGlobal: bool = False,
    ) -> Thread:
        """
        Start a chat with a user or list of users.

        **Parameters**
        - **userId** : ID of the User or List of User IDs.
        - **message** : Initial Message of the Chat.
        - **title** : Title of the Chat.
        - **content** : Content of the Chat.
        - **isGlobal** : If the Chat is Global or not.
        - **publishToGlobal** : If the Chat should be shown on Global or not.

        **Returns**
        - **Success** : :class:`Thread <aminodorksfix.lib.util.objects.Thread>`

        - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = {
            "title": title,
            "inviteeUids": [userId] if isinstance(userId, str) else userId,
            "initialMessageContent": message,
            "content": content,
            "type": 0,
            "publishToGlobal": 0,
            "timestamp": int(timestamp() * 1000),
        }

        data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread",
            data=data,
            headers=self.parse_headers(data=data),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return Thread(loads(response.text)["thread"]).Thread

    def invite_to_chat(self, userId: List[str] | str, chatId: str) -> int:
        """
        Invite a User or List of Users to a Chat.

        **Parameters**
            - **userId** : ID of the User or List of User IDs.
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps(
            {
                "uids": [userId] if isinstance(userId, str) else userId,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/member/invite",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def add_to_favorites(self, userId: str) -> int:
        """
        Add a User to your Favorites

        **Parameters**
            - **userId** : ID of the User

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{self.__endpoint}/s/user-group/quick-access/{userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def send_coins(
        self, coins: int, blogId: str = None, chatId: str = None, objectId: str = None
    ) -> int:
        """
        Send coins to a Blog or Chat.

        **Parameters**
            - **coins** : Amount of coins to send.
            - **blogId** : ID of the Blog. (for Blogs)
            - **chatId** : ID of the Chat. (for Chats)
            - **objectId** : ID of the Object. (for other objects)
            - **transactionId** : ID of the Transaction. (optional)

        **Returns**
            - **Success** : 200 (int)
            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        url = None

        data = {
            "coins": coins,
            "tippingContext": {
                "transactionId": str(UUID(hexlify(urandom(16)).decode("ascii")))
            },
            "timestamp": int(timestamp() * 1000),
        }

        if blogId:
            url = f"{self.__endpoint}/s/blog/{blogId}/tipping"
        if chatId:
            url = f"{self.__endpoint}/s/chat/thread/{chatId}/tipping"
        if objectId:
            data["objectId"] = objectId
            data["objectType"] = 2
            url = f"{self.__endpoint}/s/tipping"

        if not url:
            raise SpecifyType()

        data = dumps(data)

        response = self._session.post(
            url=url,
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def thank_tip(self, chatId: str, userId: str) -> int:
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/"
            + f"thread/{chatId}/tipping/tipped-users/{userId}/thank",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
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
        data = dumps({"targetUidList": userId, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/" + f"user-profile/{self.profile.userId}/joined",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
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
            url=f"{self.__endpoint}/s/user-profile/"
            + f"{self.profile.userId}/joined/{userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
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
            url=f"{self.__endpoint}/s/block/{userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
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
            url=f"{self.__endpoint}/s/block/{userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def flag(
        self, reason: str, flagType: int, userId: str, asGuest: bool = False
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

        data = dumps(
            {
                "flagType": flagType,
                "message": reason,
                "objectId": userId,
                "objectType": 0,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/{'g-flag' if asGuest else 'flag'}",
            data=data,
            headers=self.parse_headers(data=data),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def send_message(
        self,
        chatId: str,
        message: str = None,
        messageType: int = 0,
        file: BinaryIO = None,
        fileType: str = None,
        replyTo: str = None,
        mentionUserIds: List[str] = [],
        stickerId: str = None,
        embedId: str = None,
        embedType: int = None,
        embedLink: str = None,
        embedTitle: str = None,
        embedContent: str = None,
        embedImage: BinaryIO = None,
    ) -> int:
        """
        Send a Message to a Chat.

        **Parameters**
            - **message** : Message to be sent
            - **chatId** : ID of the Chat.
            - **file** : File to be sent.
            - **fileType** : Type of the file.
                - ``audio``, ``image``, ``gif``
            - **messageType** : Type of the Message.
            - **mentionUserIds** : List of User IDS to mention. '@' needed
                                                            in the Message.
            - **replyTo** : Message ID to reply to.
            - **stickerId** : Sticker ID to be sent.
            - **embedTitle** : Title of the Embed.
            - **embedContent** : Content of the Embed.
            - **embedLink** : Link of the Embed.
            - **embedImage** : Image of the Embed.
            - **embedId** : ID of the Embed.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        if message and not file:
            message = message.replace("<$", "‎‏").replace("$>", "‬‭")

        mentions = list(map(lambda user_id: {"uid": user_id}, mentionUserIds))
        embed_media = None

        if embedImage:
            embed_media = [[100, self.upload_media(embedImage, "image"), None]]

        data = {
            "type": messageType,
            "content": message,
            "clientRefId": int(timestamp() / 10 % 1000000000),
            "attachedObject": {
                "objectId": embedId,
                "objectType": embedType,
                "link": embedLink,
                "title": embedTitle,
                "content": embedContent,
                "mediaList": embed_media or embedImage,
            },
            "extensions": {"mentionedArray": mentions},
            "timestamp": int(timestamp() * 1000),
        }

        if replyTo:
            data["replyMessageId"] = replyTo

        if stickerId:
            data["content"] = None
            data["stickerId"] = stickerId
            data["type"] = 3

        if file:
            data["content"] = None
            if fileType == "audio":
                data["type"] = 2
                data["mediaType"] = 110

            elif fileType == "image":
                data["mediaType"] = 100
                data["mediaUploadValueContentType"] = "image/jpg"
                data["mediaUhqEnabled"] = True

            elif fileType == "gif":
                data["mediaType"] = 100
                data["mediaUploadValueContentType"] = "image/gif"
                data["mediaUhqEnabled"] = True
            else:
                raise SpecifyType(fileType)
            data["mediaUploadValue"] = b64encode(file.read()).decode()

        data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/message",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def full_embed(self, link: str, image: BinaryIO, message: str, chatId: str) -> int:
        data = {
            "type": 0,
            "content": message,
            "extensions": {
                "linkSnippetList": [
                    {
                        "link": link,
                        "mediaType": 100,
                        "mediaUploadValue": b64encode(image.read()).decode(),
                        "mediaUploadValueContentType": "image/png",
                    }
                ]
            },
            "clientRefId": int(timestamp() / 10 % 100000000),
            "timestamp": int(timestamp() * 1000),
            "attachedObject": None,
        }

        data = dumps(data)
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/message",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_message(
        self, chatId: str, messageId: str, asStaff: bool = False, reason: str = None
    ) -> int:
        """
        Delete a Message from a Chat.

        **Parameters**
            - **messageId** : ID of the Message.
            - **chatId** : ID of the Chat.
            - **asStaff** : If execute as a Staff member (Leader or Curator).
            - **reason** : Reason of the action to show on the
                                                        Moderation History.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        if not asStaff:
            response = self._session.delete(
                url=f"{self.__endpoint}/s/chat/thread/"
                + f"{chatId}/message/{messageId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)

            return response.status_code

        data: Dict[str, str | Dict[str, str] | int] = {
            "adminOpName": 102,
            "timestamp": int(timestamp() * 1000),
        }
        if asStaff and reason:
            data["adminOpNote"] = {"content": reason}

        dumped_data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/"
            + f"{chatId}/message/{messageId}/admin",
            headers=self.parse_headers(data=dumped_data),
            data=dumped_data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def mark_as_read(self, chatId: str, messageId: str) -> int:
        """
        Mark a Message from a Chat as Read.

        **Parameters**
            - **messageId** : ID of the Message.
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        data = dumps({"messageId": messageId, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/mark-as-read",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def edit_chat(
        self,
        chatId: str,
        doNotDisturb: bool = None,
        pinChat: bool = None,
        title: str = None,
        icon: str = None,
        backgroundImage: str = None,
        content: str = None,
        announcement: str = None,
        coHosts: list = None,
        keywords: List[str] = None,
        pinAnnouncement: bool = None,
        canTip: bool = None,
        viewOnly: bool = None,
        canInvite: bool = None,
        fansOnly: bool = None,
    ) -> List[int]:
        """
        Send a Message to a Chat.

        **Parameters**
            - **chatId** : ID of the Chat.
            - **title** : Title of the Chat.
            - **content** : Content of the Chat.
            - **icon** : Icon of the Chat.
            - **backgroundImage** : Url of the Background Image of the Chat.
            - **announcement** : Announcement of the Chat.
            - **pinAnnouncement** : If the Chat Announcement should Pinned
                                                                    or not.
            - **coHosts** : List of User IDS to be Co-Host.
            - **keywords** : List of Keywords of the Chat.
            - **viewOnly** : If the Chat should be on View Only or not.
            - **canTip** : If the Chat should be Tippable or not.
            - **canInvite** : If the Chat should be Invitable or not.
            - **fansOnly** : If the Chat should be Fans Only or not.
            - **publishToGlobal** : If the Chat should show on Public Chats
                                                                    or not.
            - **doNotDisturb** : If the Chat should Do Not Disturb or not.
            - **pinChat** : If the Chat should Pinned or not.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        res = []

        if doNotDisturb:
            disturb_data = dumps(
                {"alertOption": 2, "timestamp": int(timestamp() * 1000)}
            )

            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/"
                + f"thread/{chatId}/member/{self._profile.userId}/alert",
                data=disturb_data,
                headers=self.parse_headers(data=disturb_data),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)
        if pinChat:
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/pin",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)

        if backgroundImage:
            background_data = dumps(
                {
                    "media": [100, backgroundImage, None],
                    "timestamp": int(timestamp() * 1000),
                }
            )

            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}"
                + f"/member/{self._profile.userId}/background",
                data=background_data,
                headers=self.parse_headers(data=background_data),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)

        if coHosts:
            co_host_data = dumps(
                {"uidList": coHosts, "timestamp": int(timestamp() * 1000)}
            )

            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/co-host",
                data=co_host_data,
                headers=self.parse_headers(data=co_host_data),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)

        if viewOnly:
            if viewOnly:
                response = self._session.post(
                    url=f"{self.__endpoint}/s/chat/"
                    + f"thread/{chatId}/view-only/enable",
                    headers=self.parse_headers(
                        type="application/x-www-form-urlencoded"
                    ),
                    proxies=getattr(self, "_Client__proxies"),
                    verify=getattr(self, "_Client__certificate_path", None),
                )
                if response.status_code != 200:
                    res.append(CheckException(response.text))
                else:
                    res.append(response.status_code)

        if not canInvite:
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/"
                + f"thread/{chatId}/members-can-invite/disable",
                headers=self.parse_headers(type="application/x-www-form-urlencoded"),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)

        if canTip:
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/"
                + f"{chatId}/tipping-perm-status/enable",
                headers=self.parse_headers(type="application/x-www-form-urlencoded"),
                proxies=getattr(self, "_Client__proxies"),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                res.append(CheckException(response.text))
            else:
                res.append(response.status_code)

        data: Dict[str, Any] = {"timestamp": int(timestamp() * 1000)}

        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if icon:
            data["icon"] = icon
        if keywords:
            data["keywords"] = keywords
        if announcement:
            data["extensions"] = {"announcement": announcement}
        if pinAnnouncement:
            data["extensions"] = {"pinAnnouncement": pinAnnouncement}
        if fansOnly:
            data["extensions"] = {"fansOnly": fansOnly}

        dumped_data = dumps(data)

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}",
            headers=self.parse_headers(data=dumped_data),
            data=dumped_data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            res.append(CheckException(response.text))
        else:
            res.append(response.status_code)

        return res

    def transfer_host(self, chatId: str, userIds: List[str]) -> int:
        data = dumps({"uidList": userIds, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/transfer-organizer",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def accept_host(self, chatId: str, requestId: str) -> int:
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/"
            + f"{chatId}/transfer-organizer/{requestId}/accept",
            headers=self.parse_headers(type="application/x-www-form-urlencoded"),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def kick(self, userId: str, chatId: str, allowRejoin: bool = True):
        response = self._session.delete(
            url=f"{self.__endpoint}/s/chat/thread"
            + f"/{chatId}/member/{userId}?allowRejoin={int(allowRejoin)}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def join_chat(self, chatId: str) -> int:
        """
        Join an Chat.

        **Parameters**
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/"
            + f"thread/{chatId}/member/{self._profile.userId}",
            headers=self.parse_headers(type="application/x-www-form-urlencoded"),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def leave_chat(self, chatId: str) -> int:
        """
        Leave an Chat.

        **Parameters**
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{self.__endpoint}/s/chat/thread/"
            + f"{chatId}/member/{self.profile.userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def delete_chat(self, chatId: str) -> int:
        """
        Delete a Chat.

        **Parameters**
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.delete(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def subscribe(self, userId: str, autoRenew: bool = False) -> int:
        data = dumps(
            {
                "paymentContext": {
                    "transactionId": str(UUID(hexlify(urandom(16)).decode("ascii"))),
                    "isAutoRenew": autoRenew,
                },
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/influencer/{userId}/subscribe",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def promotion(self, noticeId: str, type: str = "accept") -> int:
        response = self._session.post(
            url=f"{self.__endpoint}/s/notice/{noticeId}/{type}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def play_quiz_raw(
        self, quizId: str, quizAnswerList: List[Any], quizMode: int = 0
    ) -> int:
        data = dumps(
            {
                "mode": quizMode,
                "quizAnswerList": quizAnswerList,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{quizId}/quiz/result",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def play_quiz(
        self,
        quizId: str,
        questionIdsList: List[Any],
        answerIdsList: List[Any],
        quizMode: int = 0,
    ) -> int:
        quizAnswerList = []

        for question, answer in zip(questionIdsList, answerIdsList):
            part = dumps(
                {"optIdList": [answer], "quizQuestionId": question, "timeSpent": 0.0}
            )

            quizAnswerList.append(loads(part))

        data = dumps(
            {
                "mode": quizMode,
                "quizAnswerList": quizAnswerList,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{quizId}/quiz/result",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def vc_permission(self, chatId: str, permission: int) -> int:
        """Voice Chat Join Permissions
        1 - Open to Everyone
        2 - Approval Required
        3 - Invite Only
        """
        data = dumps(
            {"vvChatJoinType": permission, "timestamp": int(timestamp() * 1000)}
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/vvchat-permission",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_vc_reputation_info(self, chatId: str) -> VcReputation:
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/avchat-reputation",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return VcReputation(loads(response.text)).VcReputation

    def claim_vc_reputation(self, chatId: str) -> VcReputation:
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/avchat-reputation",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return VcReputation(loads(response.text)).VcReputation

    def get_all_users(
        self, type: str = "recent", start: int = 0, size: int = 25
    ) -> UserProfileCountList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/user-profile"
            + f"?type={type}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )

        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileCountList(loads(response.text)).UserProfileCountList

    def get_online_users(self, start: int = 0, size: int = 25) -> UserProfileCountList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/live-layer?"
            + f"topic=ndtopic:x{self.__comId}:"
            + f"online-members&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileCountList(loads(response.text)).UserProfileCountList

    def get_online_favorite_users(
        self, start: int = 0, size: int = 25
    ) -> UserProfileCountList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/user-group/"
            + f"quick-access?type=online&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileCountList(loads(response.text)).UserProfileCountList

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
            url=f"{self.__endpoint}/s/user-profile/{userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfile(loads(response.text)["userProfile"]).UserProfile

    def get_user_following(
        self, userId: str, start: int = 0, size: int = 25
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
            url=f"{self.__endpoint}/s/user-profile/"
            + f"{userId}/joined?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def get_user_followers(
        self, userId: str, start: int = 0, size: int = 25
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
            url=f"{self.__endpoint}/s/user-profile/"
            + f"{userId}/member?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def get_user_checkins(self, userId: str) -> UserCheckIns:
        response = self._session.get(
            url=f"{self.__endpoint}/s/check-in/stats/{userId}"
            + f"?timezone={-timezone // 1000}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserCheckIns(loads(response.text)).UserCheckIns

    def get_user_blogs(self, userId: str, start: int = 0, size: int = 25) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog?"
            + f"type=user&q={userId}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def get_user_wikis(self, userId: str, start: int = 0, size: int = 25) -> WikiList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/item?type=user-all"
            + f"&start={start}&size={size}&cv=1.2&uid={userId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies"),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WikiList(loads(response.text)["itemList"]).WikiList

    def get_user_achievements(self, userId: str) -> UserAchievements:
        response = self._session.get(
            url=f"{self.__endpoint}/s/user-profile/{userId}/achievements",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserAchievements(loads(response.text)["achievements"]).UserAchievements

    def get_influencer_fans(
        self, userId: str, start: int = 0, size: int = 25
    ) -> InfluencerFans:
        response = self._session.get(
            url=f"{self.__endpoint}/s/influencer/"
            + f"{userId}/fans?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return InfluencerFans(loads(response.text)).InfluencerFans

    def get_blocked_users(self, start: int = 0, size: int = 25) -> UserProfileList:
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
            url=f"{self.__endpoint}/s/block?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def get_blocker_users(self, start: int = 0, size: int = 25) -> List[str]:
        """
        List of Users that are Blocking the User.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`List of User IDs <List>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        response = self._session.get(
            url=f"{self.__endpoint}/s/block/" + f"full-list?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)["blockerUidList"]

    def search_users(
        self, nickname: str, start: int = 0, size: int = 25
    ) -> UserProfileList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/user-profile?"
            + f"type=name&q={nickname}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def get_saved_blogs(self, start: int = 0, size: int = 25) -> UserSavedBlogs:
        response = self._session.get(
            url=f"{self.__endpoint}/s/bookmark?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserSavedBlogs(loads(response.text)["bookmarkList"]).UserSavedBlogs

    def get_leaderboard_info(
        self, type: LeaderboardType, start: int = 0, size: int = 25
    ) -> UserProfileList:
        if LeaderboardType.LAST_DAY == type:
            response = self._session.get(
                url=f"{self.__cross_point}/community/leaderboard"
                + f"?rankingType=1&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif LeaderboardType.LAST_WEEK == type:
            response = self._session.get(
                url=f"{self.__cross_point}/community/leaderboard"
                + f"?rankingType=2&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif LeaderboardType.REP == type:
            response = self._session.get(
                url=f"{self.__cross_point}/community/leaderboard"
                + f"?rankingType=3&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif LeaderboardType.CHECK == type:
            response = self._session.get(
                url=f"{self.__cross_point}/community/leaderboard" + "?rankingType=4",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        else:
            response = self._session.get(
                url=f"{self.__cross_point}/community/leaderboard"
                + f"?rankingType=5&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["userProfileList"]).UserProfileList

    def get_wiki_info(self, wikiId: str) -> GetWikiInfo:
        response = self._session.get(
            url=f"{self.__endpoint}/s/item/{wikiId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return GetWikiInfo(loads(response.text)).GetWikiInfo

    def get_recent_wiki_items(self, start: int = 0, size: int = 25) -> WikiList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/item?type="
            + f"catalog-all&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WikiList(loads(response.text)["itemList"]).WikiList

    def get_wiki_categories(self, start: int = 0, size: int = 25) -> WikiCategoryList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/item-category?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WikiCategoryList(
            loads(response.text)["itemCategoryList"]
        ).WikiCategoryList

    def get_wiki_category(
        self, categoryId: str, start: int = 0, size: int = 25
    ) -> WikiCategory:
        response = self._session.get(
            url=f"{self.__endpoint}/s/item-category"
            + f"/{categoryId}?start={start}&size={size}s",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WikiCategory(loads(response.text)).WikiCategory

    def get_tipped_users(
        self,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        chatId: str = None,
        start: int = 0,
        size: int = 25,
    ) -> TippedUsersSummary:
        response = None

        if blogId or quizId:
            if quizId:
                blogId = quizId
            response = self._session.get(
                url=f"{self.__endpoint}/s/blog/{blogId}/tipping/"
                + f"tipped-users-summary?start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif wikiId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/item/{wikiId}/tipping/"
                + f"tipped-users-summary?start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif chatId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/"
                + f"tipping/tipped-users-summary?start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        else:
            raise SpecifyType()

        if response.status_code != 200:
            return CheckException(response.text)

        return TippedUsersSummary(loads(response.text)).TippedUsersSummary

    def get_chat_threads(self, start: int = 0, size: int = 25) -> ThreadList:
        """
        List of Chats the account is in.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Chat List
                            <aminodorksfix.lib.util.ThreadList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread?type=joined-me"
            + f"&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return ThreadList(loads(response.text)["threadList"]).ThreadList

    def get_public_chat_threads(
        self, type: str = "recommended", start: int = 0, size: int = 25
    ) -> ThreadList:
        """
        List of Public Chats of the Community.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Chat List
                            <aminodorksfix.lib.util.ThreadList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread?type=public-"
            + f"all&filterType={type}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return ThreadList(loads(response.text)["threadList"]).ThreadList

    def get_chat_thread(self, chatId: str) -> Thread:
        """
        Get the Chat Object from an Chat ID.

        **Parameters**
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : :meth:`Chat Object <aminodorksfix.lib.util.Thread>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return Thread(loads(response.text)["thread"]).Thread

    def get_chat_messages(
        self, chatId: str, size: int = 25, pageToken: str = None
    ) -> MessageList:
        """
        List of Messages from an Chat.

        **Parameters**
            - **chatId** : ID of the Chat.
            - *size* : Size of the list.
            - *pageToken* : Next Page Token.

        **Returns**
            - **Success** : :meth:`Message List
                            <aminodorksfix.lib.util.MessageList>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        if pageToken is not None:
            url = (
                f"{self.__endpoint}/s/chat/thread/{chatId}/message"
                + f"?v=2&pagingType=t&pageToken={pageToken}&size={size}"
            )
        else:
            url = (
                f"{self.__endpoint}/s/chat/thread/{chatId}/message"
                + f"?v=2&pagingType=t&size={size}"
            )

        response = self._session.get(
            url,
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return GetMessages(loads(response.text)).GetMessages

    def get_message_info(self, chatId: str, messageId: str) -> Message:
        """
        Information of an Message from an Chat.

        **Parameters**
            - **chatId** : ID of the Chat.
            - **message** : ID of the Message.

        **Returns**
            - **Success** : :meth:`Message Object
                            <aminodorksfix.lib.util.Message>`

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}" + f"/message/{messageId}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return Message(loads(response.text)["message"]).Message

    def get_blog_info(
        self,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        fileId: str = None,
    ) -> SharedFolderFile | GetBlogInfo | GetWikiInfo:
        if blogId or quizId:
            if quizId:
                blogId = quizId
            response = self._session.get(
                url=f"{self.__endpoint}/s/blog/{blogId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
            return GetBlogInfo(loads(response.text)).GetBlogInfo

        elif wikiId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/item/{wikiId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
            return GetWikiInfo(loads(response.text)).GetWikiInfo

        elif fileId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/shared-folder/files/{fileId}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
            if response.status_code != 200:
                return CheckException(response.text)
            return SharedFolderFile(loads(response.text)["file"]).SharedFolderFile

        raise SpecifyType()

    def get_blog_comments(
        self,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        fileId: str = None,
        sorting: str = "newest",
        start: int = 0,
        size: int = 25,
    ) -> CommentList:
        sorting_type = COMMENTS_SORTING_MAP.get(sorting)
        if not sorting_type:
            raise WrongType(sorting)

        if blogId or quizId:
            if quizId:
                blogId = quizId
            response = self._session.get(
                url=f"{self.__endpoint}/s/blog/{blogId}/comment?"
                + f"sort={sorting_type}&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif wikiId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/item/{wikiId}/comment?"
                + f"sort={sorting_type}&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif fileId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/shared-folder/files/{fileId}"
                + f"/comment?sort={sorting_type}&start={start}&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        else:
            raise SpecifyType()

        if response.status_code != 200:
            return CheckException(response.text)

        return CommentList(loads(response.text)["commentList"]).CommentList

    def get_blog_categories(self, size: int = 25) -> BlogCategoryList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog-category?size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogCategoryList(
            loads(response.text)["blogCategoryList"]
        ).BlogCategoryList

    def get_blogs_by_category(
        self, categoryId: str, start: int = 0, size: int = 25
    ) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog-category/{categoryId}"
            + f"/blog-list?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def get_quiz_rankings(
        self, quizId: str, start: int = 0, size: int = 25
    ) -> QuizRankings:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog/{quizId}"
            + f"/quiz/result?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return QuizRankings(loads(response.text)).QuizRankings

    def get_wall_comments(
        self, userId: str, sorting: str, start: int = 0, size: int = 25
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
            url=f"{self.__endpoint}/s/user-profile/{userId}"
            + f"/comment?sort={sorting}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommentList(loads(response.text)["commentList"]).CommentList

    def get_recent_blogs(
        self, pageToken: str = None, start: int = 0, size: int = 25
    ) -> BlogList:
        if pageToken:
            url = (
                f"{self.__endpoint}/s/feed/blog-all?pagingType="
                + f"t&pageToken={pageToken}&size={size}"
            )
        else:
            url = (
                f"{self.__endpoint}/s/feed/blog-all?pagingType="
                + f"t&start={start}&size={size}"
            )

        response = self._session.get(
            url,
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return RecentBlogs(loads(response.text)).RecentBlogs

    def get_chat_users(
        self, chatId: str, start: int = 0, size: int = 25
    ) -> UserProfileList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}/member"
            + f"?start={start}&size={size}&type=default&cv=1.2",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileList(loads(response.text)["memberList"]).UserProfileList

    def get_notifications(self, start: int = 0, size: int = 25) -> NotificationList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/notification?"
            + f"pagingType=t&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return NotificationList(
            loads(response.text)["notificationList"]
        ).NotificationList

    def get_notices(self, start: int = 0, size: int = 25) -> NoticeList:
        """
        :param start: Start of the List (Start: 0)
        :param size: Amount of Notices to Show
        :return: Notices List
        """
        response = self._session.get(
            url=f"{self.__endpoint}/s/notice?type=usersV2"
            + f"&status=1&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return NoticeList(loads(response.text)["noticeList"]).NoticeList

    def get_sticker_pack_info(self, sticker_pack_id: str) -> StickerCollection:
        response = self._session.get(
            url=f"{self.__endpoint}/s/sticker-collection"
            + f"/{sticker_pack_id}?includeStickers=true",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return StickerCollection(
            loads(response.text)["stickerCollection"]
        ).StickerCollection

    def get_sticker_packs(self) -> StickerCollection:
        response = self._session.get(
            url=f"{self.__endpoint}/s/sticker-collection?includeStickers"
            + "=false&type=my-active-collection",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return StickerCollection(
            loads(response.text)["stickerCollection"]
        ).StickerCollection

    def get_community_stickers(self) -> CommunityStickerCollection:
        response = self._session.get(
            url=f"{self.__endpoint}/s/sticker-collection?" + "type=community-shared",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return CommunityStickerCollection(
            loads(response.text)
        ).CommunityStickerCollection

    def get_sticker_collection(self, collectionId: str) -> StickerCollection:
        response = self._session.get(
            url=f"{self.__endpoint}/s/sticker-collection"
            + f"/{collectionId}?includeStickers=true",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return StickerCollection(
            loads(response.text)["stickerCollection"]
        ).StickerCollection

    def get_shared_folder_info(self) -> GetSharedFolderInfo:
        response = self._session.get(
            url=f"{self.__endpoint}/s/shared-folder/stats",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return GetSharedFolderInfo(loads(response.text)["stats"]).GetSharedFolderInfo

    def get_shared_folder_files(
        self, type: str = "latest", start: int = 0, size: int = 25
    ) -> SharedFolderFileList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/shared-folder/files?"
            + f"type={type}&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return SharedFolderFileList(
            loads(response.text)["fileList"]
        ).SharedFolderFileList

    def moderation_history(
        self,
        userId: str = None,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        fileId: str = None,
        size: int = 25,
    ) -> AdminLogList:
        if userId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?objectId={userId}"
                + f"&objectType=0&pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif blogId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?objectId={blogId}"
                + f"&objectType=1&pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif quizId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?objectId={quizId}"
                + f"&objectType=1&pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif wikiId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?objectId={wikiId}"
                + f"&objectType=2&pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        elif fileId:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?objectId={fileId}"
                + f"&objectType=109&pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        else:
            response = self._session.get(
                url=f"{self.__endpoint}/s/admin/operation?"
                + f"pagingType=t&size={size}",
                headers=self.parse_headers(),
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        if response.status_code != 200:
            return CheckException(response.text)

        return AdminLogList(loads(response.text)["adminLogList"]).AdminLogList

    def feature(
        self,
        time: int,
        userId: str = None,
        chatId: str = None,
        blogId: str = None,
        wikiId: str = None,
    ) -> Dict[str, Any]:
        chosen_time = (
            FEATURE_CHAT_TIME_MAP.get(time, 3600)
            if chatId
            else FEATURE_ITEMS_TIME_MAP.get(time, 86400)
        )

        data = {
            "adminOpName": 114,
            "adminOpValue": {"featuredDuration": chosen_time},
            "timestamp": int(timestamp() * 1000),
        }

        if userId:
            data["adminOpValue"] = {"featuredType": 4}
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile/{userId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif blogId:
            data["adminOpValue"] = {"featuredType": 1}
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{blogId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif wikiId:
            data["adminOpValue"] = {"featuredType": 1}
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif chatId:
            data["adminOpValue"] = {"featuredType": 5}
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )
        else:
            raise SpecifyType()
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def unfeature(
        self,
        userId: str = None,
        chatId: str = None,
        blogId: str = None,
        wikiId: str = None,
    ) -> Dict[str, Any]:
        data = dumps(
            {
                "adminOpName": 114,
                "timestamp": int(timestamp() * 1000),
                "adminOpValue": {"featuredType": 0},
            }
        )

        if userId:
            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile/{userId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif blogId:
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{blogId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif wikiId:
            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif chatId:
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        else:
            raise SpecifyType()
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def hide(
        self,
        userId: str = None,
        chatId: str = None,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        fileId: str = None,
        reason: str = None,
    ) -> Dict[str, Any]:
        data = {
            "adminOpNote": {"content": reason},
            "timestamp": int(timestamp() * 1000),
        }

        if userId:
            data["adminOpName"] = 18
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile/{userId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif blogId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 9
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{blogId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif quizId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 9
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{quizId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif wikiId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 9
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif chatId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 9
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif fileId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 9
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/shared-folder/files/{fileId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        else:
            raise SpecifyType()
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def unhide(
        self,
        userId: str = None,
        chatId: str = None,
        blogId: str = None,
        wikiId: str = None,
        quizId: str = None,
        fileId: str = None,
        reason: str = None,
    ) -> Dict[str, Any]:
        data = {
            "adminOpNote": {"content": reason},
            "timestamp": int(timestamp() * 1000),
        }

        if userId:
            data["adminOpName"] = 19
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/user-profile/{userId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif blogId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 0
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{blogId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif quizId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 0
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/blog/{quizId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif wikiId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 0
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/item/{wikiId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif chatId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 0
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/chat/thread/{chatId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        elif fileId:
            data["adminOpName"] = 110
            data["adminOpValue"] = 0
            data = dumps(data)
            response = self._session.post(
                url=f"{self.__endpoint}/s/shared-folder/files/{fileId}/admin",
                headers=self.parse_headers(data=data),
                data=data,
                proxies=getattr(self, "_Client__proxies", None),
                verify=getattr(self, "_Client__certificate_path", None),
            )

        else:
            raise SpecifyType()

        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def edit_titles(
        self, userId: str, titles: List[str], colors: List[str]
    ) -> Dict[str, Any]:
        tlt = []
        for title, color in zip(titles, colors):
            tlt.append({"title": title, "color": color})

        data = dumps(
            {
                "adminOpName": 207,
                "adminOpValue": {"titles": tlt},
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/{userId}/admin",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def warn(self, userId: str, reason: str = None) -> Dict[str, Any]:
        data = dumps(
            {
                "uid": userId,
                "title": "Custom",
                "content": reason,
                "attachedObject": {"objectId": userId, "objectType": 0},
                "penaltyType": 0,
                "adminOpNote": {},
                "noticeType": 7,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/notice",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def strike(
        self, userId: str, hours: int, title: str = None, reason: str = None
    ) -> Dict[str, Any]:
        data = dumps(
            {
                "uid": userId,
                "title": title,
                "content": reason,
                "attachedObject": {"objectId": userId, "objectType": 0},
                "penaltyType": 1,
                "penaltyValue": hours * 3600,
                "adminOpNote": {},
                "noticeType": 4,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/notice",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def ban(self, userId: str, reason: str, banType: int = None) -> Dict[str, Any]:
        data = dumps(
            {
                "reasonType": banType,
                "note": {"content": reason},
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/{userId}/ban",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def unban(self, userId: str, reason: str) -> Dict[str, Any]:
        data = dumps(
            {"note": {"content": reason}, "timestamp": int(timestamp() * 1000)}
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/{userId}/unban",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def reorder_featured_users(self, userIds: list) -> Dict[str, Any]:
        data = dumps({"uidList": userIds, "timestamp": int(timestamp() * 1000)})

        response = self._session.post(
            url=f"{self.__endpoint}/s/user-profile/featured/reorder",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return loads(response.text)

    def get_hidden_blogs(self, start: int = 0, size: int = 25) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/feed/blog-disabled?"
            + f"start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)
        else:
            return BlogList(loads(response.text)["blogList"]).BlogList

    def get_featured_users(
        self, start: int = 0, size: int = 25
    ) -> UserProfileCountList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/user-profile?"
            + f"type=featured&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return UserProfileCountList(loads(response.text)).UserProfileCountList

    def review_quiz_questions(self, quizId: str) -> QuizQuestionList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog/{quizId}?action=review",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return QuizQuestionList(
            loads(response.text)["blog"]["quizQuestionList"]
        ).QuizQuestionList

    def get_recent_quiz(self, start: int = 0, size: int = 25) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/blog?type=quizzes-recent"
            + f"&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def get_trending_quiz(self, start: int = 0, size: int = 25) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/feed/quiz-trending"
            + f"?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def get_best_quiz(self, start: int = 0, size: int = 25) -> BlogList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/feed/quiz-best-quizzes"
            + f"?start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return BlogList(loads(response.text)["blogList"]).BlogList

    def apply_avatar_frame(self, avatarId: str, applyToAll: bool = True) -> int:
        """
        Apply avatar frame.

        **Parameters**
            - **avatarId** : ID of the avatar frame.
            - **applyToAll** : Apply to all.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`

        """

        data = {
            "frameId": avatarId,
            "applyToAll": 0,
            "timestamp": int(timestamp() * 1000),
        }

        if applyToAll:
            data["applyToAll"] = 1

        data = dumps(data)
        response = self._session.post(
            url=f"{self.__endpoint}/s/avatar-frame/apply",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def invite_to_vc(self, chatId: str, userId: str) -> int:
        """
        Invite a User to a Voice Chat

        **Parameters**
            - **chatId** - ID of the Chat
            - **userId** - ID of the User

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <aminodorksfix.lib.util.exceptions>`
        """

        data = dumps({"uid": userId})

        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/{chatId}"
            + "/vvchat-presenter/invite/",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def add_poll_option(self, blogId: str, question: str) -> int:
        data = dumps(
            {
                "mediaList": None,
                "title": question,
                "type": 0,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/blog/{blogId}/poll/option",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def create_wiki_category(
        self, title: str, parentCategoryId: str, content: str = None
    ) -> int:
        data = dumps(
            {
                "content": content,
                "icon": None,
                "label": title,
                "mediaList": None,
                "parentCategoryId": parentCategoryId,
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/item-category",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def create_shared_folder(self, title: str) -> int:
        data = dumps({"title": title, "timestamp": int(timestamp() * 1000)})
        response = self._session.post(
            url=f"{self.__endpoint}/s/shared-folder/folders",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def submit_to_wiki(self, wikiId: str, message: str) -> int:
        data = dumps(
            {"message": message, "itemId": wikiId, "timestamp": int(timestamp() * 1000)}
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/knowledge-base-request",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def accept_wiki_request(
        self, requestId: str, destinationCategoryIdList: List[Any]
    ) -> int:
        data = dumps(
            {
                "destinationCategoryIdList": destinationCategoryIdList,
                "actionType": "create",
                "timestamp": int(timestamp() * 1000),
            }
        )

        response = self._session.post(
            url=f"{self.__endpoint}/s/knowledge-base-request" + f"/{requestId}/approve",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def reject_wiki_request(self, requestId: str) -> int:
        data = dumps({})

        response = self._session.post(
            url=f"{self.__endpoint}/s/knowledge-base-request" + f"/{requestId}/reject",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code

    def get_wiki_submissions(self, start: int = 0, size: int = 25) -> WikiRequestList:
        response = self._session.get(
            url=f"{self.__endpoint}/s/knowledge-base-request"
            + f"?type=all&start={start}&size={size}",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return WikiRequestList(
            loads(response.text)["knowledgeBaseRequestList"]
        ).WikiRequestList

    def get_live_layer(self) -> LiveLayer:
        response = self._session.get(
            url=f"{self.__endpoint}/s/live-layer/homepage?v=2",
            headers=self.parse_headers(),
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return LiveLayer(loads(response.text)["liveLayerList"]).LiveLayer

    def apply_bubble(self, bubbleId: str, chatId: str, applyToAll: bool = False) -> int:
        data = {
            "applyToAll": 0,
            "bubbleId": bubbleId,
            "threadId": chatId,
            "timestamp": int(timestamp() * 1000),
        }

        if applyToAll is True:
            data["applyToAll"] = 1

        data = dumps(data)
        response = self._session.post(
            url=f"{self.__endpoint}/s/chat/thread/apply-bubble",
            headers=self.parse_headers(data=data),
            data=data,
            proxies=getattr(self, "_Client__proxies", None),
            verify=getattr(self, "_Client__certificate_path", None),
        )
        if response.status_code != 200:
            return CheckException(response.text)

        return response.status_code
