from enum import Enum

__all__ = ["LeaderboardType"]


class LeaderboardType(Enum):
    LAST_DAY = 24,
    LAST_WEEK = 7,
    REP = 3,
    CHECK = 4,
    QUIZ = 5
