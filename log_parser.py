import os
import glob
import re


def get_latest_log():
    """
    Returns the newest Roblox log file path.
    """
    log_dir = os.path.expanduser(r"~\AppData\Local\Roblox\logs")
    log_files = glob.glob(os.path.join(log_dir, "*.log"))

    if not log_files:
        return None

    return max(log_files, key=os.path.getmtime)


def parse_session_info(log_path):
    """
    Extracts basic session info from Roblox logs:
    - place_id
    - username
    - display_name
    """

    place_id = None
    username = None
    display_name = None

    with open(log_path, "r", errors="ignore") as f:
        for line in f:

            # Detect place id (join message)
            if "Joining game" in line:
                match = re.search(r"place (\d+)", line)
                if match:
                    place_id = int(match.group(1))

            # Alternative teleport format
            if "doTeleport" in line:
                match = re.search(r'"PlaceId"%3a(\d+)', line)
                if match:
                    place_id = int(match.group(1))

            # Username (common log format)
            if "Username:" in line:
                match = re.search(r"Username:\s*(\w+)", line)
                if match:
                    username = match.group(1)

            # Display name (if present in logs)
            if "DisplayName:" in line:
                match = re.search(r"DisplayName:\s*(.+)", line)
                if match:
                    display_name = match.group(1).strip()

    return {
        "place_id": place_id,
        "username": username,
        "display_name": display_name,
    }
