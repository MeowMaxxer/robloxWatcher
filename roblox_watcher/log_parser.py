"""
log_parser.py — Extracts session information from a Roblox log file.

Roblox writes plain-text logs to:
    %LOCALAPPDATA%\\Roblox\\logs\\*.log

Each line is prefixed with a timestamp and source tag, e.g.:
    2024-01-01T12:00:00.000Z,Info,... [FLog::Output] ...

The patterns below are read-only; the library never writes to the log directory.
"""

import glob
import os
import re
from typing import Optional

from .models import SessionInfo

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# "! Joining game '...' place 123456 ..."
_RE_JOIN_PLACE = re.compile(r"! Joining game.*?place (\d+)")

# Teleport URL: "PlaceId"%3a123456
_RE_TELEPORT_PLACE = re.compile(r'"PlaceId"%3[aA](\d+)')

# Username reported during startup, e.g.:
#   [FLog::Output] Hello from the client! Username: Builderman
_RE_USERNAME = re.compile(r"Hello from the client! Username:\s*(\S+)", re.IGNORECASE)

# Display name reported during startup, e.g.:
#   [FLog::Output] DisplayName: Build Man
_RE_DISPLAY_NAME = re.compile(r"DisplayName:\s*(.+?)(?:\s*[\[\|]|$)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_latest_log(log_dir: Optional[str] = None) -> Optional[str]:
    """
    Return the path of the most recently modified .log file in log_dir.

    Parameters
    ----------
    log_dir :
        Directory to scan. Defaults to %LOCALAPPDATA%\\Roblox\\logs.

    Returns
    -------
    str or None
        Absolute path to the newest log file, or None if the directory
        is empty or does not exist.
    """
    if log_dir is None:
        log_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Roblox",
            "logs",
        )

    pattern = os.path.join(log_dir, "*.log")
    log_files = glob.glob(pattern)
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)


def parse_session_info(log_path: str) -> SessionInfo:
    """
    Parse log_path and return a SessionInfo with whatever fields could be extracted.

    The entire file is scanned so that the last matched Place ID wins
    (i.e. teleports override the initial join).

    Parameters
    ----------
    log_path :
        Absolute path to a Roblox .log file.

    Returns
    -------
    SessionInfo
        Fields that could not be found are left as None.
    """
    info = SessionInfo()

    try:
        with open(log_path, "r", errors="ignore") as fh:
            for line in fh:
                _apply_place_id(line, info)
                _apply_username(line, info)
                _apply_display_name(line, info)
    except OSError:
        pass  # Log file disappeared between the call and the read.

    return info


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _apply_place_id(line: str, info: SessionInfo) -> None:
    """Update info.place_id if line contains a place-ID pattern."""
    m = _RE_JOIN_PLACE.search(line)
    if m:
        info.place_id = int(m.group(1))
        return

    m = _RE_TELEPORT_PLACE.search(line)
    if m:
        info.place_id = int(m.group(1))


def _apply_username(line: str, info: SessionInfo) -> None:
    """Update info.username if line contains a username pattern."""
    if info.username:
        return  # Already found; username does not change mid-session.
    m = _RE_USERNAME.search(line)
    if m:
        info.username = m.group(1).strip()


def _apply_display_name(line: str, info: SessionInfo) -> None:
    """Update info.display_name if line contains a display-name pattern."""
    if info.display_name:
        return  # Already found.
    m = _RE_DISPLAY_NAME.search(line)
    if m:
        display = m.group(1).strip()
        if display:  # Guard against empty captures.
            info.display_name = display
