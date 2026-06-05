"""
watcher.py — High-level session monitor for Roblox.

Example
-------
::

    from roblox_watcher import RobloxWatcher

    def on_join(info):
        print(info)  # prints all available fields

    watcher = RobloxWatcher(interval=5, enrich=True)
    watcher.watch(on_join=on_join)
"""

import time
from typing import Callable, Optional

import psutil

from .log_parser import get_latest_log, parse_session_info
from .models import SessionInfo

_ROBLOX_PROCESS_NAME = "RobloxPlayerBeta.exe"


class RobloxWatcher:
    """
    Polls the Roblox log directory and fires callbacks when the player
    joins a new game or Roblox closes.

    Parameters
    ----------
    interval :
        Polling cadence in seconds. Defaults to ``5``.
    enrich :
        When ``True`` (default), automatically call
        :meth:`~roblox_watcher.models.SessionInfo.enrich` after each game
        join so that ``on_join`` receives full API data (profile, avatar
        URLs, game info, etc.).  Set to ``False`` to skip API calls.
    log_dir :
        Override the default log directory
        (``%LOCALAPPDATA%\\Roblox\\logs``). Useful for testing.
    badge_limit :
        How many recent badges to fetch when *enrich* is ``True`` (1–100).
    """

    def __init__(
        self,
        interval: float = 5,
        enrich: bool = True,
        fetch_images: bool = True,
        log_dir: Optional[str] = None,
        badge_limit: int = 10,
    ) -> None:
        self.interval = interval
        self.enrich = enrich
        self.fetch_images = fetch_images
        self.log_dir = log_dir
        self.badge_limit = badge_limit
        self._last_place_id: Optional[int] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def is_running() -> bool:
        """Return ``True`` if a Roblox player process is currently active."""
        return any(
            p.info["name"] == _ROBLOX_PROCESS_NAME
            for p in psutil.process_iter(["name"])
        )

    def get_current_session(self, enrich: Optional[bool] = None) -> Optional[SessionInfo]:
        """
        Return a :class:`~roblox_watcher.models.SessionInfo` for the active
        session, or ``None`` if Roblox is not running or no log is available.

        Parameters
        ----------
        enrich :
            Override the instance-level ``enrich`` setting for this call.
        """
        if not self.is_running():
            return None
        log_path = get_latest_log(self.log_dir)
        if log_path is None:
            return None
        info = parse_session_info(log_path)
        should_enrich = self.enrich if enrich is None else enrich
        if should_enrich:
            info.enrich(badge_limit=self.badge_limit, fetch_images=self.fetch_images)
        return info

    def watch(
        self,
        on_join: Optional[Callable[[SessionInfo], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Block and poll until interrupted (``KeyboardInterrupt``).

        Parameters
        ----------
        on_join :
            Called with a :class:`~roblox_watcher.models.SessionInfo`
            whenever a new game is detected (including teleports).
            If ``enrich=True``, the object is already fully populated with
            API data before this callback fires.
        on_close :
            Called with no arguments when Roblox closes.
        """
        self._running = True
        enrich_note = " + API enrichment" if self.enrich else ""
        print(
            f"roblox_watcher: polling every {self.interval}s"
            f"{enrich_note} — Ctrl+C to stop."
        )

        try:
            while self._running:
                self._tick(on_join=on_join, on_close=on_close)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nroblox_watcher: stopped.")
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal :meth:`watch` to exit after the current sleep."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(
        self,
        on_join: Optional[Callable[[SessionInfo], None]],
        on_close: Optional[Callable[[], None]],
    ) -> None:
        if not self.is_running():
            if self._last_place_id is not None:
                self._last_place_id = None
                if on_close:
                    on_close()
            return

        log_path = get_latest_log(self.log_dir)
        if log_path is None:
            return

        info = parse_session_info(log_path)
        if info.place_id and info.place_id != self._last_place_id:
            self._last_place_id = info.place_id
            if self.enrich:
                info.enrich(badge_limit=self.badge_limit, fetch_images=self.fetch_images)
            if on_join:
                on_join(info)
