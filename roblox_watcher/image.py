"""
image.py — In-memory image container for avatar and thumbnail data.

``AvatarImage`` holds raw PNG/Webp bytes fetched from the Roblox CDN.
No file is ever written to disk unless the caller explicitly asks for it.

Typical use
-----------
::

    info = RobloxWatcher().get_current_session()

    # Display in a tkinter label
    from PIL import ImageTk
    photo = ImageTk.PhotoImage(data=info.avatar_headshot.to_base64())

    # Embed in an HTML page / notification
    src = info.avatar_headshot.to_data_uri()   # "data:image/png;base64,..."

    # Pass raw bytes to any image library
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(info.avatar_headshot.bytes))

    # Only write to disk when the user explicitly wants it
    info.avatar_headshot.save("headshot.png")
"""

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
from typing import Optional


class AvatarImage:
    """
    An in-memory image fetched from the Roblox CDN.

    Parameters
    ----------
    data :
        Raw image bytes (PNG or Webp).
    fmt :
        MIME sub-type string, e.g. ``"png"`` or ``"webp"``.
    source_url :
        The CDN URL the bytes were fetched from (informational only).
    """

    def __init__(
        self,
        data: bytes,
        fmt: str = "png",
        source_url: Optional[str] = None,
    ) -> None:
        self._data = data
        self._fmt = fmt.lower().lstrip(".")
        self.source_url = source_url

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def bytes(self) -> bytes:
        """Raw image bytes — pass directly to any image library."""
        return self._data

    @property
    def size(self) -> int:
        """Size of the image in bytes."""
        return len(self._data)

    @property
    def format(self) -> str:
        """Image format string, e.g. ``"png"`` or ``"webp"``."""
        return self._fmt

    # ------------------------------------------------------------------
    # Encoding helpers  (no disk I/O)
    # ------------------------------------------------------------------

    def to_base64(self) -> str:
        """
        Return the image as a plain base64-encoded string.

        Use this when a library expects base64 without the ``data:`` prefix
        (e.g. ``PIL.ImageTk.PhotoImage(data=...)``).
        """
        return base64.b64encode(self._data).decode("ascii")

    def to_data_uri(self) -> str:
        """
        Return a ``data:`` URI suitable for an HTML ``<img src="...">``
        attribute or a desktop notification icon field.

        Example output::

            data:image/png;base64,iVBORw0KGgo...
        """
        return f"data:image/{self._fmt};base64,{self.to_base64()}"

    def to_bytesio(self) -> io.BytesIO:
        """
        Return a seeked :class:`io.BytesIO` wrapping the image bytes.

        Equivalent to ``io.BytesIO(avatar.bytes)`` but the stream position
        is reset to 0 for you.

        Works as a drop-in file-like object for libraries such as Pillow,
        OpenCV, or requests::

            from PIL import Image
            img = Image.open(info.avatar_headshot.to_bytesio())
        """
        buf = io.BytesIO(self._data)
        buf.seek(0)
        return buf

    # ------------------------------------------------------------------
    # Optional disk helpers  (only when the caller explicitly wants a file)
    # ------------------------------------------------------------------

    def save(self, path: str) -> str:
        """
        Write the image to *path* on disk.

        Parameters
        ----------
        path :
            Destination file path, e.g. ``"avatar.png"``.

        Returns
        -------
        str
            The absolute path of the written file.
        """
        with open(path, "wb") as fh:
            fh.write(self._data)
        return os.path.abspath(path)

    def show(self) -> None:
        """
        Open the image in the system's default viewer.

        A temporary file is created, opened, and scheduled for deletion —
        no permanent file is left on disk.  Useful for quick debugging.
        """
        suffix = f".{self._fmt}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(self._data)
            tmp_path = tmp.name

        # Open with the OS default handler
        if sys.platform == "win32":
            os.startfile(tmp_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f"open {tmp_path!r}")
        else:
            os.system(f"xdg-open {tmp_path!r}")

        # Clean up after a brief delay so the viewer has time to load
        import threading

        def _remove():
            import time
            time.sleep(5)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        threading.Thread(target=_remove, daemon=True).start()

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AvatarImage(format={self._fmt!r}, size={self.size} bytes, "
            f"source_url={self.source_url!r})"
        )

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return bool(self._data)
