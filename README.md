# roblox-watcher

A Python library that tracks your active Roblox session by reading the log files Roblox already writes to your PC. No code is injected into Roblox, no memory is read, and no API keys are required.

```python
from roblox_watcher import RobloxWatcher

def on_join(info):
    print(f"Joined {info.game.name} as {info.username} ({info.display_name})")
    print(f"Avatar: {info.avatar_headshot.to_data_uri()}")  # ready to use in any UI

RobloxWatcher().watch(on_join=on_join)
```

---

## How it works

Roblox writes timestamped log files to `%LOCALAPPDATA%\Roblox\logs\` as you play. `roblox-watcher` watches those files for join and teleport events, parses out your Place ID and username, then hits Roblox's own public REST API to fill in the rest. Everything is read-only.

---

## What it gives you

| Where it comes from | Data |
|---------------------|------|
| Log file | Place ID, username, display name |
| Roblox Users API | User ID, bio, join date, ban status |
| Roblox Thumbnails API | Avatar headshot + full body (in memory) |
| Roblox Friends API | Friend count |
| Roblox Badges API | Recent badges |
| Roblox Games API | Game name, creator, player count, visit count, thumbnail |

---

## Requirements

- Windows (Roblox desktop client)
- Python 3.9 or newer
- [`psutil`](https://pypi.org/project/psutil/) — the only external dependency

---

## Installation

```bash
pip install psutil
```

Then copy the `roblox_watcher/` folder into your project.

---

## Usage

### Watch for game joins

```python
from roblox_watcher import RobloxWatcher

def on_join(info):
    print(info)  # pretty-prints all available fields

def on_close():
    print("Roblox closed")

RobloxWatcher().watch(on_join=on_join, on_close=on_close)
```

### One-shot snapshot

```python
from roblox_watcher import RobloxWatcher

info = RobloxWatcher().get_current_session()
if info:
    print(info.username)
    print(info.game.name)
```

### Working with avatar images

Avatar images are returned as `AvatarImage` objects — raw bytes held in memory, no files written to disk unless you ask.

```python
def on_join(info):
    img = info.avatar_headshot

    # Use directly in tkinter / Pillow
    from PIL import ImageTk
    photo = ImageTk.PhotoImage(data=img.to_base64())

    # Embed in HTML or a desktop notification
    src = img.to_data_uri()  # "data:image/png;base64,..."

    # Pass raw bytes to any image library
    from PIL import Image
    import io
    pil_img = Image.open(img.to_bytesio())

    # Only write to disk if you actually want a file
    img.save("headshot.png")

    # Quick preview in your default image viewer (temp file, auto-deleted)
    img.show()
```

### Skip image fetching (metadata only)

```python
RobloxWatcher(fetch_images=False).watch(on_join=on_join)
# info.avatar_headshot_url is still set, but info.avatar_headshot is None
```

### Use the API helpers on their own

```python
from roblox_watcher import api

user_id  = api.get_user_id("Builderman")
profile  = api.get_user_profile(user_id)
headshot = api.fetch_avatar_headshot(user_id)        # AvatarImage in memory
full     = api.fetch_avatar_full(user_id, size="720x720")
friends  = api.get_friend_count(user_id)
badges   = api.get_badges(user_id, limit=25)

universe_id = api.get_universe_id(place_id=6872265039)
game_meta   = api.get_game_info(universe_id)
thumb       = api.fetch_image_from_url(api.get_game_thumbnail_url(universe_id))
```

---

## Command line

```bash
python -m roblox_watcher                   # default — 5s interval, full API data
python -m roblox_watcher --interval 3      # poll every 3 seconds
python -m roblox_watcher --no-enrich       # log data only, no API calls
python -m roblox_watcher --no-images       # metadata only, skip image bytes
python -m roblox_watcher --save-avatar     # write headshot PNG to disk on join
python -m roblox_watcher --show-avatar     # open headshot in default viewer on join
python -m roblox_watcher --badge-limit 25  # fetch up to 25 recent badges
```

Sample output:

```
==================================================
[Game Joined]
==================================================
Username     : Builderman
Nickname     : Build Man
User ID      : 156
Joined Roblox: 2006-02-27
Friends      : 312
Banned       : False
Bio          : Welcome to Roblox!
Headshot     : <AvatarImage 42301 bytes>
Full avatar  : <AvatarImage 89204 bytes>
Badges       : Welcome To The Club, Warrior, Homestead

Place ID     : 6872265039
Game         : Natural Disaster Survival
Creator      : Shedletsky
Playing now  : 14,302
Total visits : 1,234,567,890
Game thumb   : <AvatarImage 31088 bytes>
```

---

## API reference

### `RobloxWatcher`

```python
RobloxWatcher(
    interval=5,        # polling cadence in seconds
    enrich=True,       # fetch Roblox API data on each join
    fetch_images=True, # fetch avatar/thumbnail bytes into memory
    badge_limit=10,    # how many recent badges to fetch (1–100)
    log_dir=None,      # override log directory (useful for testing)
)
```

| Method | Returns | Description |
|--------|---------|-------------|
| `is_running()` | `bool` | `True` if Roblox is open |
| `get_current_session()` | `SessionInfo \| None` | One-shot snapshot |
| `watch(on_join, on_close)` | — | Blocking poll loop |
| `stop()` | — | Stop the loop after the current sleep |

---

### `SessionInfo`

| Field | Type | Source |
|-------|------|--------|
| `place_id` | `int \| None` | Log |
| `username` | `str \| None` | Log |
| `display_name` | `str \| None` | Log / API |
| `user_id` | `int \| None` | API |
| `description` | `str \| None` | API |
| `account_created` | `str \| None` | API |
| `is_banned` | `bool \| None` | API |
| `avatar_headshot_url` | `str \| None` | API |
| `avatar_full_url` | `str \| None` | API |
| `avatar_headshot` | `AvatarImage \| None` | API (bytes) |
| `avatar_full` | `AvatarImage \| None` | API (bytes) |
| `friend_count` | `int \| None` | API |
| `badges` | `list[dict]` | API |
| `game` | `GameInfo \| None` | API |

Call `info.enrich()` manually if you have an un-enriched snapshot.

---

### `AvatarImage`

Holds image bytes in memory. No files are written unless you call `.save()`.

| Method / Property | Description |
|-------------------|-------------|
| `.bytes` | Raw image bytes |
| `.size` | Size in bytes |
| `.format` | `"png"` or `"webp"` |
| `.to_base64()` | Base64 string (no `data:` prefix) |
| `.to_data_uri()` | `data:image/png;base64,...` |
| `.to_bytesio()` | `io.BytesIO` — drop-in file-like object |
| `.save(path)` | Write to disk, returns absolute path |
| `.show()` | Open in default viewer (temp file, auto-deleted) |

---

### `GameInfo`

| Field | Type |
|-------|------|
| `universe_id` | `int \| None` |
| `name` | `str \| None` |
| `creator` | `str \| None` |
| `playing` | `int \| None` |
| `visits` | `int \| None` |
| `thumbnail_url` | `str \| None` |
| `thumbnail` | `AvatarImage \| None` |

---

### `api` module

All functions return `None` or `[]` on failure — no exceptions are raised.

| Function | Returns |
|----------|---------|
| `api.get_user_id(username)` | `int \| None` |
| `api.get_user_profile(user_id)` | `dict \| None` |
| `api.get_avatar_headshot_url(user_id, size, fmt)` | `str \| None` |
| `api.get_avatar_full_url(user_id, size, fmt)` | `str \| None` |
| `api.fetch_avatar_headshot(user_id, size, fmt)` | `AvatarImage \| None` |
| `api.fetch_avatar_full(user_id, size, fmt)` | `AvatarImage \| None` |
| `api.fetch_image_from_url(url)` | `AvatarImage \| None` |
| `api.get_universe_id(place_id)` | `int \| None` |
| `api.get_game_info(universe_id)` | `dict \| None` |
| `api.get_game_thumbnail_url(universe_id, size, fmt)` | `str \| None` |
| `api.get_friend_count(user_id)` | `int \| None` |
| `api.get_badges(user_id, limit)` | `list[dict]` |

---

## Notes

- Log file patterns are unofficial and may change with Roblox updates. If a field comes back `None`, open an issue with a sanitised log snippet.
- Only works on Windows (where the Roblox desktop client runs).
- No Roblox ToS violations — read-only, no injection, no memory access.

---

## License

MIT
