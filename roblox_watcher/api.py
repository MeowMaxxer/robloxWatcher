"""
api.py — Roblox public REST API helpers.

All functions are stateless and return ``None`` on any failure so callers
never have to catch exceptions themselves.

Endpoints used (all public, no auth required)
---------------------------------------------
- https://users.roblox.com/v1/usernames/users          resolve username → user_id
- https://users.roblox.com/v1/users/{user_id}          full profile
- https://thumbnails.roblox.com/v1/users/avatar-headshot  avatar headshot URL
- https://thumbnails.roblox.com/v1/users/avatar        full avatar URL
- https://games.roblox.com/v1/games?universeIds=...    game info
- https://apis.roblox.com/universes/v1/places/{place_id}/universe  place → universe_id
- https://badges.roblox.com/v1/users/{user_id}/badges  badge list (first page)
- https://friends.roblox.com/v1/users/{user_id}/friends/count  friend count
"""

from __future__ import annotations

import urllib.request
import urllib.error
import json
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .image import AvatarImage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIMEOUT = 8  # seconds per HTTP request


def _get(url: str) -> Optional[dict]:
    """Perform a GET request and return the parsed JSON body, or None on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "roblox-watcher/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _post(url: str, payload: dict) -> Optional[dict]:
    """Perform a POST request with a JSON body and return parsed response."""
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "roblox-watcher/0.2.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _fetch_bytes(url: str) -> Optional[bytes]:
    """Fetch a URL and return the raw response body as bytes, or None on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "roblox-watcher/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError):
        return None


# ---------------------------------------------------------------------------
# User resolution
# ---------------------------------------------------------------------------


def get_user_id(username: str) -> Optional[int]:
    """
    Resolve a Roblox username to its numeric user ID.

    Parameters
    ----------
    username :
        Exact Roblox account name (case-insensitive).

    Returns
    -------
    int or None
        Numeric user ID, or ``None`` if the user was not found.
    """
    body = _post(
        "https://users.roblox.com/v1/usernames/users",
        {"usernames": [username], "excludeBannedUsers": False},
    )
    if not body:
        return None
    data = body.get("data", [])
    return int(data[0]["id"]) if data else None


def get_user_profile(user_id: int) -> Optional[dict]:
    """
    Fetch the full public profile for *user_id*.

    Returned keys include: ``id``, ``name``, ``displayName``,
    ``description``, ``created``, ``isBanned``, ``externalAppDisplayName``.

    Returns
    -------
    dict or None
    """
    return _get(f"https://users.roblox.com/v1/users/{user_id}")


# ---------------------------------------------------------------------------
# Avatars
# ---------------------------------------------------------------------------


def get_avatar_headshot_url(
    user_id: int,
    size: str = "420x420",
    fmt: str = "Png",
) -> Optional[str]:
    """
    Return the CDN URL for the player's circular headshot thumbnail.

    Parameters
    ----------
    user_id :
        Numeric Roblox user ID.
    size :
        One of ``"48x48"``, ``"50x50"``, ``"60x60"``, ``"75x75"``,
        ``"100x100"``, ``"110x110"``, ``"150x150"``, ``"180x180"``,
        ``"352x352"``, ``"420x420"`` (default).
    fmt :
        ``"Png"`` (default) or ``"Webp"``.

    Returns
    -------
    str or None
        Direct HTTPS image URL, or ``None`` on failure.
    """
    url = (
        "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size={size}&format={fmt}&isCircular=false"
    )
    body = _get(url)
    if not body:
        return None
    data = body.get("data", [])
    if not data:
        return None
    return data[0].get("imageUrl")


def get_avatar_full_url(
    user_id: int,
    size: str = "420x420",
    fmt: str = "Png",
) -> Optional[str]:
    """
    Return the CDN URL for the player's full-body avatar thumbnail.

    Parameters mirror :func:`get_avatar_headshot_url`.
    Valid sizes: ``"30x30"``, ``"48x48"``, ``"60x60"``, ``"75x75"``,
    ``"100x100"``, ``"110x110"``, ``"140x140"``, ``"150x150"``,
    ``"150x200"``, ``"180x180"``, ``"250x250"``, ``"352x352"``,
    ``"420x420"`` (default), ``"720x720"``.
    """
    url = (
        "https://thumbnails.roblox.com/v1/users/avatar"
        f"?userIds={user_id}&size={size}&format={fmt}&isCircular=false"
    )
    body = _get(url)
    if not body:
        return None
    data = body.get("data", [])
    if not data:
        return None
    return data[0].get("imageUrl")


def fetch_avatar_headshot(
    user_id: int,
    size: str = "420x420",
    fmt: str = "Png",
) -> "Optional[AvatarImage]":
    """
    Fetch the player's headshot thumbnail and return it as an
    :class:`~roblox_watcher.image.AvatarImage` held entirely in memory.

    No file is written to disk.  The caller decides what to do with the
    bytes — display them in a GUI, encode them as a data URI, pass them
    to Pillow, etc.

    Parameters
    ----------
    user_id :
        Numeric Roblox user ID.
    size :
        Thumbnail size (default ``"420x420"``). Other valid values:
        ``"48x48"``, ``"50x50"``, ``"60x60"``, ``"75x75"``,
        ``"100x100"``, ``"110x110"``, ``"150x150"``, ``"180x180"``,
        ``"352x352"``.
    fmt :
        ``"Png"`` (default) or ``"Webp"``.

    Returns
    -------
    AvatarImage or None
        In-memory image object, or ``None`` on any failure.

    Examples
    --------
    Display in tkinter::

        from PIL import ImageTk
        photo = ImageTk.PhotoImage(data=info.avatar_headshot.to_base64())

    Embed in HTML::

        src = info.avatar_headshot.to_data_uri()
        # → "data:image/png;base64,iVBORw0KGgo..."

    Open in Pillow::

        from PIL import Image
        img = Image.open(info.avatar_headshot.to_bytesio())

    Save only when you want a file::

        info.avatar_headshot.save("headshot.png")
    """
    from .image import AvatarImage

    cdn_url = get_avatar_headshot_url(user_id, size=size, fmt=fmt)
    if not cdn_url:
        return None
    raw = _fetch_bytes(cdn_url)
    if not raw:
        return None
    return AvatarImage(raw, fmt=fmt.lower(), source_url=cdn_url)


def fetch_avatar_full(
    user_id: int,
    size: str = "420x420",
    fmt: str = "Png",
) -> "Optional[AvatarImage]":
    """
    Fetch the player's full-body avatar thumbnail and return it as an
    :class:`~roblox_watcher.image.AvatarImage` held entirely in memory.

    Parameters mirror :func:`fetch_avatar_headshot`.
    Valid sizes: ``"30x30"``, ``"48x48"``, ``"60x60"``, ``"75x75"``,
    ``"100x100"``, ``"110x110"``, ``"140x140"``, ``"150x150"``,
    ``"150x200"``, ``"180x180"``, ``"250x250"``, ``"352x352"``,
    ``"420x420"`` (default), ``"720x720"``.
    """
    from .image import AvatarImage

    cdn_url = get_avatar_full_url(user_id, size=size, fmt=fmt)
    if not cdn_url:
        return None
    raw = _fetch_bytes(cdn_url)
    if not raw:
        return None
    return AvatarImage(raw, fmt=fmt.lower(), source_url=cdn_url)


def fetch_image_from_url(url: str, fmt: str = "png") -> "Optional[AvatarImage]":
    """
    Fetch *any* Roblox CDN image URL into memory.

    Useful for game thumbnails or badge icons whose URL you already have.

    Parameters
    ----------
    url :
        Direct CDN URL (e.g. from :func:`get_game_thumbnail_url`).
    fmt :
        Image format hint for the resulting :class:`AvatarImage`
        (default ``"png"``).

    Returns
    -------
    AvatarImage or None
    """
    from .image import AvatarImage

    raw = _fetch_bytes(url)
    if not raw:
        return None
    return AvatarImage(raw, fmt=fmt, source_url=url)


# ---------------------------------------------------------------------------
# Game / place info
# ---------------------------------------------------------------------------


def get_universe_id(place_id: int) -> Optional[int]:
    """
    Resolve a Place ID to its parent Universe ID.

    Returns
    -------
    int or None
    """
    body = _get(
        f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    )
    if not body:
        return None
    return body.get("universeId")


def get_game_info(universe_id: int) -> Optional[dict]:
    """
    Return public metadata for a game by its Universe ID.

    Returned keys include: ``id``, ``name``, ``description``,
    ``creator`` (dict with ``name``), ``playing``, ``visits``,
    ``maxPlayers``, ``created``, ``updated``, ``genre``, ``isAllGenre``,
    ``isFavoritedByUser``, ``favoritedCount``.

    Returns
    -------
    dict or None
    """
    body = _get(
        f"https://games.roblox.com/v1/games?universeIds={universe_id}"
    )
    if not body:
        return None
    data = body.get("data", [])
    return data[0] if data else None


def get_game_thumbnail_url(
    universe_id: int,
    size: str = "768x432",
    fmt: str = "Png",
) -> Optional[str]:
    """
    Return the CDN URL for the game's thumbnail image.

    Parameters
    ----------
    universe_id :
        Universe (not Place) ID.
    size :
        One of ``"768x432"`` (default), ``"576x324"``, ``"480x270"``,
        ``"384x216"``, ``"256x144"``.
    fmt :
        ``"Png"`` (default) or ``"Webp"``.

    Returns
    -------
    str or None
    """
    url = (
        "https://thumbnails.roblox.com/v1/games/icons"
        f"?universeIds={universe_id}&returnPolicy=PlaceHolder"
        f"&size={size}&format={fmt}&isCircular=false"
    )
    body = _get(url)
    if not body:
        return None
    data = body.get("data", [])
    return data[0].get("imageUrl") if data else None


# ---------------------------------------------------------------------------
# Social / badges
# ---------------------------------------------------------------------------


def get_friend_count(user_id: int) -> Optional[int]:
    """
    Return the player's friend count.

    Returns
    -------
    int or None
    """
    body = _get(
        f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    )
    if not body:
        return None
    return body.get("count")


def get_badges(user_id: int, limit: int = 10) -> list[dict]:
    """
    Return the first page of badges awarded to *user_id*.

    Each badge dict contains: ``id``, ``name``, ``description``,
    ``displayIconImageId``, ``awarder`` (the game that awarded it).

    Parameters
    ----------
    limit :
        Page size (1–100). Defaults to 10.

    Returns
    -------
    list[dict]
        Empty list on failure or if the user has no badges.
    """
    body = _get(
        f"https://badges.roblox.com/v1/users/{user_id}/badges"
        f"?limit={limit}&sortOrder=Desc"
    )
    if not body:
        return []
    return body.get("data", [])
