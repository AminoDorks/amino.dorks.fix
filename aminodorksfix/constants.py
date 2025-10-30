__all__ = [
    "PREFIX",
    "SIGNATURE_KEY",
    "DEVICE_KEY",
    "GENERATOR_HEADERS",
    "GENERATOR_URL",
    "USER_AGENT",
    "API_URL",
    "WS_URL",
    "DEFAULT_HEADERS",
    "GENDERS_MAP",
    "MEDIA_TYPES_MAP",
    "COMMENTS_SORTING_MAP",
    "SUPPORTED_LANGAUGES",
    "FEATURE_CHAT_TIME_MAP",
    "FEATURE_ITEMS_TIME_MAP",
    "ACM_MODULES_MAP",
    "RECONNECT_TIME"
]

PREFIX = bytes.fromhex("52")
SIGNATURE_KEY = bytes.fromhex("EAB4F1B9E3340CD1631EDE3B587CC3EBEDF1AFA9")
DEVICE_KEY = bytes.fromhex("AE49550458D8E7C51D566916B04888BFB8B3CA7D")
RECONNECT_TIME = 180

GENERATOR_HEADERS = {
    "Content-Type": "application/json; charset=utf8",
    "CONNECTION": "Keep-Alive",
    "Authorization": None
}

GENERATOR_URL = "https://aminodorks.agency/api/v1"

USER_AGENT = (
    "Dalvik/2.1.0 (Linux; U; Android 10; M2006C3MNG "
    "Build/QP1A.190711.020;com.narvii.amino.master/4.3.3121)"
)

API_URL = "https://service.aminoapps.com/api/v1"
WS_URL = "wss://ws1.aminoapps.com"

DEFAULT_HEADERS = {
    "Accept-Language": "en-US",
    "NDCLANG": "en",
    "Content-Type": "application/json; charset=utf-8",
    "Host": "service.aminoapps.com",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "Keep-Alive",
    "User-Agent": (
        "Dalvik/2.1.0 (Linux; U; Android 10; M2006C3MNG "
        "Build/QP1A.190711.020;com.narvii.amino.master/4.3.3121)"
    )
}

GENDERS_MAP = {
    "1": "male",
    "2": "female",
    "255": "non-binary"
}

MEDIA_TYPES_MAP = {
    "audio": "audio/aac",
    "image": "image/jpg"
}

COMMENTS_SORTING_MAP = {
    "newest": "newest",
    "oldest": "oldest",
    "top": "vote"
}

SUPPORTED_LANGAUGES = ["en", "es", "pt", "ar", "ru", "fr", "de"]

FEATURE_CHAT_TIME_MAP = {
    1: 3600,
    2: 7200,
    3: 10800
}

FEATURE_ITEMS_TIME_MAP = {
    1: 86400,
    2: 172800,
    3: 259200
}

ACM_MODULES_MAP = {
    "chat": "module.chat.enabled",
    "livechat": "module.chat.avChat.videoEnabled",
    "screeningroom": "module.chat.avChat.screeningRoomEnabled",
    "publicchats": "module.chat.publicChat.enabled",
    "posts": "module.post.enabled",
    "ranking": "module.ranking.enabled",
    "leaderboards": "module.ranking.leaderboardEnabled",
    "featured": "module.featured.enabled",
    "featuredposts": "module.featured.postEnabled",
    "featuredusers": "module.featured.memberEnabled",
    "featuredchats": "module.featured.publicChatRoomEnabled",
    "sharedfolder": "module.sharedFolder.enabled",
    "influencer": "module.influencer.enabled",
    "catalog": "module.catalog.enabled",
    "externalcontent": "module.externalContent.enabled",
    "topiccategories": "module.topicCategories.enabled"
}
