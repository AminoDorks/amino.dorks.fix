__all__ = [
    "USER_AGENT",
    "API_URL",
    "DEFAULT_HEADERS",
    "GENDERS_MAP",
    "MEDIA_TYPES_MAP",
    "COMMENTS_SORTING_MAP",
    "SUPPORTED_LANGAUGES"
]

USER_AGENT = (
    "Dalvik/2.1.0 (Linux; U; Android 10; M2006C3MNG "
    "Build/QP1A.190711.020;com.narvii.amino.master/4.3.3121)"
)

API_URL = "https://service.aminoapps.com/api/v1"

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
