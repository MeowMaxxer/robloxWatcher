"""
__main__.py — Run the watcher from the command line.

Usage
-----
::

    python -m roblox_watcher
    python -m roblox_watcher --interval 3
    python -m roblox_watcher --no-enrich        # skip API calls
    python -m roblox_watcher --no-images        # metadata only, skip image bytes
    python -m roblox_watcher --save-avatar      # also write headshot PNG to disk
    python -m roblox_watcher --show-avatar      # open headshot in default viewer
"""

import argparse

from .watcher import RobloxWatcher
from .models import SessionInfo


def _on_join(info: SessionInfo, save_avatar: bool, show_avatar: bool) -> None:
    print("\n" + "=" * 50)
    print("[Game Joined]")
    print("=" * 50)
    print(info)

    if info.avatar_headshot:
        if save_avatar:
            name = f"avatar_{info.username or info.user_id}.png"
            path = info.avatar_headshot.save(name)
            print(f"\nHeadshot saved → {path}")

        if show_avatar:
            info.avatar_headshot.show()  # opens in default viewer, no file left behind

    print()


def _on_close() -> None:
    print("\n[Roblox closed]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="roblox_watcher",
        description="Monitor Roblox game sessions via log files.",
    )
    parser.add_argument(
        "--interval", type=float, default=5.0, metavar="SECONDS",
        help="Polling interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--no-enrich", dest="enrich", action="store_false", default=True,
        help="Disable all Roblox API calls (log data only)",
    )
    parser.add_argument(
        "--no-images", dest="fetch_images", action="store_false", default=True,
        help="Fetch metadata but skip downloading image bytes",
    )
    parser.add_argument(
        "--badge-limit", type=int, default=10, metavar="N",
        help="Recent badges to fetch (default: 10)",
    )
    parser.add_argument(
        "--save-avatar", action="store_true", default=False,
        help="Write headshot PNG to disk on each join",
    )
    parser.add_argument(
        "--show-avatar", action="store_true", default=False,
        help="Open headshot in the default image viewer on each join",
    )
    args = parser.parse_args()

    watcher = RobloxWatcher(
        interval=args.interval,
        enrich=args.enrich,
        fetch_images=args.fetch_images,
        badge_limit=args.badge_limit,
    )
    watcher.watch(
        on_join=lambda info: _on_join(
            info,
            save_avatar=args.save_avatar,
            show_avatar=args.show_avatar,
        ),
        on_close=_on_close,
    )


if __name__ == "__main__":
    main()
