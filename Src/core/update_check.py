import json
import logging
import os
import platform
import sys
import threading
import urllib.request
from pathlib import Path

from utils import APP_VERSION

logger = logging.getLogger("workshop.update")

RELEASES_URL = (
    "https://api.github.com/repos/Mitra-88/WorkshopDecompressor/releases/latest"
)
RELEASES_PREFIX = "https://github.com/Mitra-88/WorkshopDecompressor/"
OPT_OUT_ENV = "WORKSHOP_DECOMPRESSOR_NO_UPDATE_CHECK"
_CHECK_TIMEOUT = 3

_lock = threading.Lock()
_pending_notice = None


def _state_path():
    system = platform.system()

    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"

    return Path(base) / "WorkshopDecompressor" / "update-check.json"


def _parse_version(tag):
    try:
        return tuple(int(part) for part in tag.removeprefix("v").split("."))
    except ValueError:
        return None


def _read_last_notified():
    try:
        state = json.loads(_state_path().read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return state.get("last_notified")


def _write_last_notified(tag):
    try:
        path = _state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_notified": tag}), encoding="utf-8")
    except OSError:
        pass


def _latest_release():
    request = urllib.request.Request(
        RELEASES_URL,
        headers={
            "User-Agent": "WorkshopDecompressor",
            "Accept": "application/vnd.github+json",
        },
    )

    with urllib.request.urlopen(request, timeout=_CHECK_TIMEOUT) as response:
        release = json.load(response)

    tag = release.get("tag_name") or ""
    url = release.get("html_url") or ""

    if _parse_version(tag) is None or not url.startswith(RELEASES_PREFIX):
        return None

    return tag, url


def _check():
    global _pending_notice

    release = _latest_release()

    if release is None:
        return

    tag, url = release
    remote = _parse_version(tag)
    running = _parse_version(APP_VERSION)

    if remote <= running:
        return

    with _lock:
        if _read_last_notified() != tag:
            _pending_notice = (tag, url)
            _write_last_notified(tag)


def _safe_check():
    try:
        _check()
    except Exception:  # noqa: BLE001
        logger.debug("Update check skipped: problem reaching GitHub.")


def start():
    if os.environ.get(OPT_OUT_ENV):
        return

    if not (sys.stdout is not None and sys.stdout.isatty()):
        return

    threading.Thread(target=_safe_check, daemon=True).start()


def take_notice():
    with _lock:
        global _pending_notice
        notice, _pending_notice = _pending_notice, None
    return notice
