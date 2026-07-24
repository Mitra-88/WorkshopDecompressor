import platform
from datetime import datetime
from os import rmdir, scandir
from pathlib import Path
from uuid import uuid4

excluded_directories = frozenset({"Bin", "Leftover", "_internal", "Extracted-Addons"})

app_version = f"v2.7.1 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d)")


def format_time(seconds):
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)

    parts = []
    if h:
        parts.append(f"{h:.0f}h")
    if m:
        parts.append(f"{m:.0f}m")
    if s or not parts:
        parts.append(f"{s:.3f}s")

    return " ".join(parts)


def normalize_architecture(arch):
    mapping = {
        "x86_64": "64-Bit",
        "amd64": "AMD64",
        "arm64": "ARM64",
        "aarch64": "ARM64",
        "64bit": "64-Bit",
    }
    return mapping.get(arch.lower(), arch)


def get_windows_feature_update():
    if platform.system() != "Windows":
        return None

    try:
        import winreg

        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            return display_version
    except Exception:
        return None


def get_system_info():
    system = platform.system()
    arch = normalize_architecture(platform.machine())
    if system == "Windows":
        edition = platform.win32_edition()
        release = platform.release()
        version = platform.version()
        feature_update = get_windows_feature_update()
        feature_part = f"{feature_update} " if feature_update else ""
        return f"{system} {release} {feature_part}{edition} (Build {version}) {arch}".strip()
    elif system == "Linux":
        try:
            os_release = platform.freedesktop_os_release()
            if "PRETTY_NAME" in os_release:
                return f"{os_release['PRETTY_NAME']} {arch}"
            name = os_release.get("NAME", "Linux")
            version = os_release.get("VERSION", "")
            if name or version:
                return f"{name} {version} {arch}".strip()
        except OSError:
            system_name = platform.system()
            release = platform.release()
            return f"{system_name} {release} {arch}"
    elif system == "Darwin":
        mac_version, *_ = platform.mac_ver()
        return f"macOS {mac_version or platform.release()} {arch}"


def unique_name(file_path):
    p = Path(file_path)
    if not p.exists():
        return p
    counter = 1
    while True:
        candidate = p.with_name(f"{p.stem}-{counter}{p.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def remove_empty_directories(directory, excluded=excluded_directories):
    dir_path = Path(directory)
    if dir_path.name in excluded:
        return 0

    deleted = 0
    try:
        with scandir(dir_path) as entries:
            children = list(entries)
    except (PermissionError, FileNotFoundError):
        return 0

    for entry in children:
        if entry.is_dir() and entry.name not in excluded:
            deleted += remove_empty_directories(entry.path, excluded)

    try:
        with scandir(dir_path) as entries:
            if any(True for _ in entries):
                return deleted
    except (PermissionError, FileNotFoundError):
        return deleted

    try:
        rmdir(dir_path)
        return deleted + 1
    except OSError:
        return deleted
