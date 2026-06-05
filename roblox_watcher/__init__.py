"""
roblox_watcher
==============
A lightweight Python library for monitoring active Roblox sessions.

Tracks game joins and teleports, then enriches each event with data
from the public Roblox API: profile info, avatar images (in memory),
game metadata, friend count, and recent badges — all without an API key.

Typical usage
-------------
>>> from roblox_watcher import RobloxWatcher
>>> watcher = RobloxWatcher(enrich=True)
>>> watcher.watch(on_join=lambda info: print(info))
"""

from .watcher import RobloxWatcher
from .log_parser import parse_session_info, get_latest_log
from .models import SessionInfo, GameInfo
from .image import AvatarImage
from . import api

__all__ = [
    "RobloxWatcher",
    "parse_session_info",
    "get_latest_log",
    "SessionInfo",
    "GameInfo",
    "AvatarImage",
    "api",
]
__version__ = "0.3.0"
