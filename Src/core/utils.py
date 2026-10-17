import platform
import sys
import threading
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from os import process_cpu_count, rmdir, scandir
from pathlib import Path
from subprocess import DEVNULL, PIPE, SubprocessError, run

excluded_directories = frozenset({"Bin", "Leftover", "_internal", "Extracted-Addons"})

_unique_name_lock = threading.Lock()
_reserved_paths = set()


def _git_commit():
    if getattr(sys, "frozen", False):
        try:
            commit_file = Path(getattr(sys, "_MEIPASS", ".")) / "build_commit.txt"
            return commit_file.read_text(encoding="utf-8").strip() or "release"
        except OSError:
            return "release"
    try:
        result = run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        return result.stdout.strip() or "dev"
    except OSError, SubprocessError:
        return "dev"


def _build_time():
    if getattr(sys, "frozen", False):
        try:
            return datetime.fromtimestamp(Path(sys.executable).stat().st_mtime)
        except OSError:
            pass
    return datetime.now()


def _package_version(name):
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "bundled"


def _tool_versions():
    if getattr(sys, "frozen", False):
        try:
            bundled_file = Path(getattr(sys, "_MEIPASS", ".")) / "build_tools.txt"
            bundled = bundled_file.read_text(encoding="utf-8").strip()
        except OSError, ValueError:
            bundled = ""
        if bundled:
            return ", ".join(bundled.splitlines())
    return (
        f"PyInstaller {_package_version('pyinstaller')}, "
        f"Rich {_package_version('rich')}, "
        "7-Zip (bundled)"
    )


APP_VERSION = "2.9.0"
app_version = f"v{APP_VERSION} ({_git_commit()})"
build_date = _build_time().strftime("%Y-%m-%d (%A, %B %d)")
tool_versions = _tool_versions()


def extraction_workers(max_workers, cores=None):
    available = cores if cores is not None else (process_cpu_count() or 2)
    return min(max_workers, max(1, available - 2), max(1, available * 3 // 4))


def _sevenzip_pass(seven_zip_path, archive_path, output_dir):
    result = run(
        [str(seven_zip_path), "x", str(archive_path), f"-o{output_dir}", "-y"],
        stdout=DEVNULL,
        stderr=PIPE,
        text=True,
        errors="replace",
        check=False,
    )
    message = result.stderr.strip() or f"exited with code {result.returncode}"
    return result.returncode, message


def _single_inner_tar(output_dir):
    entries = list(output_dir.iterdir())
    if (
        len(entries) == 1
        and entries[0].is_file()
        and entries[0].name.lower().endswith(".tar")
    ):
        return entries[0]
    return None


def run_sevenzip_extraction(seven_zip_path, archive_path, output_dir):
    output_dir = Path(output_dir)
    returncode, message = _sevenzip_pass(seven_zip_path, archive_path, output_dir)
    extracted = any(output_dir.iterdir())

    if extracted:
        inner_tar = _single_inner_tar(output_dir)
        if inner_tar is not None:
            inner_code, inner_message = _sevenzip_pass(
                seven_zip_path, inner_tar, output_dir
            )
            if any(entry != inner_tar for entry in output_dir.iterdir()):
                inner_tar.unlink()
                extracted = True
                returncode, message = inner_code, inner_message
            elif inner_code >= 2:
                extracted = False
                returncode, message = inner_code, inner_message

    # ponytail: content presence is the truth signal because 7-Zip exits with
    # code 2 on legacy .bin addons (trailing bytes after the lzma payload) even
    # though extraction succeeds; upgrade path: run `7z t` for full crc checks.
    return extracted, returncode, message


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


def plural(count, word, plural_word=None):
    if count == 1:
        return f"{count} {word}"

    return f"{count} {plural_word or word + 's'}"


def normalize_architecture(arch: str) -> str:
    mapping = {
        "x86_64": "64-Bit",
        "amd64": "AMD64",
        "arm64": "ARM64",
        "aarch64": "ARM64",
    }
    return mapping.get(arch.lower(), arch)


def join_parts(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)


def get_windows_feature_update() -> str | None:
    if platform.system() != "Windows":
        return None

    try:
        import winreg

        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            return display_version
    except OSError:
        return None


def get_system_info() -> str:
    system = platform.system()
    arch = normalize_architecture(platform.machine())

    if system == "Windows":
        build = platform.version().split(".")[-1]
        return join_parts(
            system,
            platform.release(),
            get_windows_feature_update(),
            platform.win32_edition(),
            f"(Build {build})",
            arch,
        )

    if system == "Linux":
        try:
            os_release = platform.freedesktop_os_release()
            if "PRETTY_NAME" in os_release:
                return join_parts(os_release["PRETTY_NAME"], arch)
            name = os_release.get("NAME", "Linux")
            version = os_release.get("VERSION") or os_release.get("VERSION_ID") or ""
            return join_parts(name, version, arch)
        except AttributeError, OSError:
            return join_parts(system, platform.release(), arch)

    if system == "Darwin":
        mac_version, *_ = platform.mac_ver()
        if mac_version:
            return join_parts("macOS", mac_version, arch)
        return join_parts("macOS", f"(Darwin {platform.release()})", arch)

    return join_parts(system, platform.release(), arch)


def unique_name(file_path):
    with _unique_name_lock:
        p = Path(file_path)
        counter = 0
        while True:
            candidate = (
                p if counter == 0 else p.with_name(f"{p.stem}-{counter}{p.suffix}")
            )
            cand_str = str(candidate.absolute())

            if not candidate.exists() and cand_str not in _reserved_paths:
                _reserved_paths.add(cand_str)
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
    except PermissionError, FileNotFoundError:
        return 0

    for entry in children:
        if entry.is_dir() and entry.name not in excluded:
            deleted += remove_empty_directories(entry.path, excluded)

    try:
        with scandir(dir_path) as entries:
            if any(True for _ in entries):
                return deleted
    except PermissionError, FileNotFoundError:
        return deleted

    try:
        rmdir(dir_path)
        return deleted + 1
    except OSError:
        return deleted
