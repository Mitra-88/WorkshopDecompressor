from logging import getLogger, basicConfig, INFO
from uuid import uuid4
from datetime import datetime
from os import path, rmdir, listdir, scandir
from platform import system, architecture, win32_ver, win32_edition, freedesktop_os_release, mac_ver, machine

basicConfig(level=INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = getLogger("vae_utils")

excluded_directories = {"Bin", "Leftover", "_internal", "Extracted-Addons"}

vae_version = f"v2.4.6 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d, %Y)")

def format_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")

    if secs > 0 or not parts:
        parts.append(f"{secs:.3f}s")

    return " ".join(parts)

def normalize_architecture(arch):
    return {
        "x86_64": "64-Bit",
        "64bit": "64-Bit",
        "arm64": "ARM64",
    }.get(arch, arch)

def get_windows_info():
    try:
        version = win32_ver()[0]
        edition = win32_edition()
        arch = normalize_architecture(architecture()[0])
        return f"Windows {version} {edition} {arch}"
    except Exception as error:
        return f"Windows (Error: {error})"

def get_linux_info():
    try:
        distro = freedesktop_os_release()
        name = distro.get("NAME", "Linux")
        pretty_name = distro.get("PRETTY_NAME", "")
        version = distro.get("VERSION", "")
        version_id = distro.get("VERSION_ID", "")
        arch = normalize_architecture(architecture()[0])

        if pretty_name:
            return f"{pretty_name} {arch}"
        if version:
            return f"{version} {arch}"
        
        components = [name]
        if version_id:
            components.append(version_id)
        return f"{' '.join(components)} {arch}"

    except OSError:
        return f"Linux {normalize_architecture(architecture()[0])}"
    except Exception as error:
        return f"Linux (Error: {error})"

def get_macos_info():
    try:
        version = mac_ver()[0]
        arch = normalize_architecture(machine())
        return f"macOS {version} {arch}"
    except Exception as error:
        return f"macOS (Error: {error})"

def get_os_info():
    system_name = system()
    handlers = {
        "Windows": get_windows_info,
        "Linux": get_linux_info,
        "Darwin": get_macos_info,
    }
    handler = handlers.get(system_name)
    return handler() if handler else f"Unknown OS (System: {system_name})"

def get_executable_paths() -> dict:
    current_platform = system()
    base_path = "Bin"
    platform_paths = {
        "Windows": {"7z": "7z.exe", "fastgmad": "fastgmad.exe"},
        "Linux": {"7z": "7z", "fastgmad": "fastgmad"},
        "Darwin": {"7z": "7z", "fastgmad": "fastgmad"},
    }

    if current_platform not in platform_paths:
        msg = f"Unsupported platform: {current_platform}. Supported platforms are: Windows, Linux, macOS."
        logger.error(msg)
        raise Exception(msg)

    executable_path = {
        exe: path.join(base_path, current_platform, exe_name)
        for exe, exe_name in platform_paths[current_platform].items()
    }

    for exe, exe_path in list(executable_path.items()):
        if not path.exists(exe_path):
            logger.warning("Could not find %s at %s", exe, exe_path)
            provided = input(f"Could not find {exe} at {exe_path}. Please provide full path to {exe}: ").strip()
            if not path.exists(provided):
                logger.error("Provided path for %s does not exist: %s", exe, provided)
                raise FileNotFoundError(f"Provided path for {exe} does not exist: {provided}")
            executable_path[exe] = provided
            logger.info("Using provided path for %s: %s", exe, provided)
        else:
            logger.info("Found %s at %s", exe, exe_path)

    return executable_path

def unique_name(file_path: str) -> str:
    base, extension = path.splitext(file_path)
    new_name = f"{base}-{uuid4().hex[:7]}{extension}"
    logger.warning("Detected duplicate file. Renaming to: %s", new_name)
    return new_name

def remove_empty_directories(start_dir: str) -> None:
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                remove_empty_directories(entry.path)
                try:
                    if not listdir(entry.path):
                        rmdir(entry.path)
                        logger.info("Removed empty directory: %s", entry.path)
                except Exception as error:
                    logger.exception("Failed to remove directory: %s", entry.path)
                    handle_error(entry.path, error)
    except Exception as error:
        logger.exception("Error traversing directories starting at: %s", start_dir)
        handle_error(start_dir, error)

def handle_error(file_name: str, error: Exception) -> None:
    if isinstance(error, FileNotFoundError):
        logger.error("File not found - %s", file_name)
    elif isinstance(error, PermissionError):
        logger.error("Permission denied - %s", file_name)
    elif isinstance(error, (EOFError, ValueError)):
        logger.error("Corrupt - %s: %s", file_name, error)
    else:
        logger.exception("Unexpected error processing %s", file_name)
