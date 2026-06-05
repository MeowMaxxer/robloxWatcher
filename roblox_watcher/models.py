"""
models.py — Data containers for roblox_watcher.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .image import AvatarImage


@dataclass
class GameInfo:
    """
    Public metadata for the game the player is currently in.

    Attributes
    ----------
    universe_id : int or None
        Parent universe ID (needed for most Games API calls).
    name : str or None
        Game title as shown on the Roblox website.
    creator : str or None
        Display name of the game creator / group.
    playing : int or None
        Current concurrent player count.
    visits : int or None
        All-time visit count.
    thumbnail_url : str or None
        CDN URL for the game's thumbnail image.
    thumbnail : AvatarImage or None
        Game thumbnail fetched into memory (populated by
        :meth:`SessionInfo.enrich` when ``fetch_images=True``).
    """

    universe_id: Optional[int] = None
    name: Optional[str] = None
    creator: Optional[str] = None
    playing: Optional[int] = None
    visits: Optional[int] = None
    thumbnail_url: Optional[str] = None
    thumbnail: Optional["AvatarImage"] = None


@dataclass
class SessionInfo:
    """
    A snapshot of the current Roblox session.

    Log-derived fields
    ------------------
    place_id : int or None
        Numeric Place ID of the current game.
    username : str or None
        Roblox account name (e.g. ``"Builderman"``).
    display_name : str or None
        Player's chosen display name / nickname.

    API-enriched fields  (populated after :meth:`enrich` is called)
    ----------------------------------------------------------------
    user_id : int or None
        Numeric Roblox user ID.
    description : str or None
        Profile bio / about text.
    account_created : str or None
        ISO-8601 timestamp of account creation.
    is_banned : bool or None
        Whether the account is currently banned.
    avatar_headshot_url : str or None
        CDN URL for the headshot thumbnail (always set when available,
        regardless of ``fetch_images``).
    avatar_full_url : str or None
        CDN URL for the full-body avatar thumbnail.
    avatar_headshot : AvatarImage or None
        Headshot image bytes held in memory — ready to pass to any image
        library, encode as base64/data-URI, or display in a GUI.
        ``None`` when ``fetch_images=False`` or on network failure.
    avatar_full : AvatarImage or None
        Full-body avatar image bytes held in memory.
    friend_count : int or None
        Number of friends.
    badges : list[dict]
        Most-recent badges awarded to the player (up to 10 by default).
    game : GameInfo or None
        Metadata for the game at :attr:`place_id`.
    """

    # --- log-derived ---
    place_id: Optional[int] = None
    username: Optional[str] = None
    display_name: Optional[str] = None

    # --- API-enriched: user ---
    user_id: Optional[int] = None
    description: Optional[str] = None
    account_created: Optional[str] = None
    is_banned: Optional[bool] = None

    # CDN URLs (always populated when API is reachable)
    avatar_headshot_url: Optional[str] = None
    avatar_full_url: Optional[str] = None

    # In-memory image objects (populated when fetch_images=True)
    avatar_headshot: Optional["AvatarImage"] = None
    avatar_full: Optional["AvatarImage"] = None

    friend_count: Optional[int] = None
    badges: list = field(default_factory=list)

    # --- API-enriched: game ---
    game: Optional[GameInfo] = None

    # ------------------------------------------------------------------

    def enrich(
        self,
        badge_limit: int = 10,
        fetch_images: bool = True,
    ) -> "SessionInfo":
        """
        Fetch all available public data from the Roblox API and populate
        the enriched fields in-place.

        Images are fetched into memory as :class:`~roblox_watcher.image.AvatarImage`
        objects — no files are written to disk unless you explicitly call
        ``.save()`` on them later.

        Parameters
        ----------
        badge_limit :
            How many recent badges to fetch (1–100). Default 10.
        fetch_images :
            When ``True`` (default), fetch avatar and game thumbnail bytes
            into memory.  Set to ``False`` to populate only URLs and
            metadata, skipping the extra HTTP requests.

        Returns
        -------
        self
            Supports method chaining::

                info = watcher.get_current_session().enrich()
        """
        from . import api

        # ---- resolve user ID ----
        if self.username and self.user_id is None:
            self.user_id = api.get_user_id(self.username)

        if self.user_id:
            # Profile metadata
            profile = api.get_user_profile(self.user_id)
            if profile:
                self.description = profile.get("description") or None
                self.account_created = profile.get("created") or None
                self.is_banned = profile.get("isBanned")
                if not self.display_name:
                    self.display_name = profile.get("displayName") or None

            # CDN URLs (cheap — just JSON, no image bytes)
            self.avatar_headshot_url = api.get_avatar_headshot_url(self.user_id)
            self.avatar_full_url = api.get_avatar_full_url(self.user_id)

            # In-memory image bytes (only when requested)
            if fetch_images:
                self.avatar_headshot = api.fetch_avatar_headshot(self.user_id)
                self.avatar_full = api.fetch_avatar_full(self.user_id)

            self.friend_count = api.get_friend_count(self.user_id)
            self.badges = api.get_badges(self.user_id, limit=badge_limit)

        # ---- game info ----
        if self.place_id:
            game = GameInfo()
            game.universe_id = api.get_universe_id(self.place_id)
            if game.universe_id:
                meta = api.get_game_info(game.universe_id)
                if meta:
                    game.name = meta.get("name")
                    creator = meta.get("creator", {})
                    game.creator = creator.get("name")
                    game.playing = meta.get("playing")
                    game.visits = meta.get("visits")
                game.thumbnail_url = api.get_game_thumbnail_url(game.universe_id)
                if fetch_images and game.thumbnail_url:
                    game.thumbnail = api.fetch_image_from_url(game.thumbnail_url)
            self.game = game

        return self

    # ------------------------------------------------------------------

    def is_log_complete(self) -> bool:
        """Return True when all log-derived fields are populated."""
        return all(
            v is not None for v in (self.place_id, self.username, self.display_name)
        )

    def is_enriched(self) -> bool:
        """Return True when API enrichment has run and found a user ID."""
        return self.user_id is not None

    def __str__(self) -> str:
        lines = []

        # User
        if self.username:
            lines.append(f"Username     : {self.username}")
        if self.display_name:
            lines.append(f"Nickname     : {self.display_name}")
        if self.user_id:
            lines.append(f"User ID      : {self.user_id}")
        if self.account_created:
            lines.append(f"Joined Roblox: {self.account_created[:10]}")
        if self.friend_count is not None:
            lines.append(f"Friends      : {self.friend_count}")
        if self.is_banned is not None:
            lines.append(f"Banned       : {self.is_banned}")
        if self.description:
            short = self.description[:80].replace("\n", " ")
            lines.append(f"Bio          : {short}{'…' if len(self.description) > 80 else ''}")

        # Images — show size if loaded, URL if not
        if self.avatar_headshot:
            lines.append(f"Headshot     : <AvatarImage {self.avatar_headshot.size} bytes>")
        elif self.avatar_headshot_url:
            lines.append(f"Headshot URL : {self.avatar_headshot_url}")

        if self.avatar_full:
            lines.append(f"Full avatar  : <AvatarImage {self.avatar_full.size} bytes>")
        elif self.avatar_full_url:
            lines.append(f"Full avt URL : {self.avatar_full_url}")

        # Badges
        if self.badges:
            names = ", ".join(b.get("name", "?") for b in self.badges[:5])
            lines.append(f"Badges       : {names}")

        # Game
        if lines and self.place_id:
            lines.append("")
        if self.place_id:
            lines.append(f"Place ID     : {self.place_id}")
        if self.game:
            if self.game.name:
                lines.append(f"Game         : {self.game.name}")
            if self.game.creator:
                lines.append(f"Creator      : {self.game.creator}")
            if self.game.playing is not None:
                lines.append(f"Playing now  : {self.game.playing:,}")
            if self.game.visits is not None:
                lines.append(f"Total visits : {self.game.visits:,}")
            if self.game.thumbnail:
                lines.append(
                    f"Game thumb   : <AvatarImage {self.game.thumbnail.size} bytes>"
                )
            elif self.game.thumbnail_url:
                lines.append(f"Game thumb   : {self.game.thumbnail_url}")

        return "\n".join(lines) if lines else "<no session data>"
