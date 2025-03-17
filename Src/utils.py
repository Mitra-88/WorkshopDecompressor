from uuid import uuid4
from os import path
from datetime import datetime
from platform import system, architecture, win32_ver, win32_edition, freedesktop_os_release, mac_ver, machine

vae_version = f"v2.4.4 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d, %Y)")

def format_time(seconds):
    hours, remaining = divmod(seconds, 3600)
    minutes, remaining = divmod(remaining, 60)
    
    if hours > 0:
        return f"{hours:.0f}h {minutes:.0f}m {remaining:.3f}s"
    if minutes > 0:
        return f"{minutes:.0f}m {remaining:.3f}s"
    return f"{remaining:.3f}s"

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

def get_executable_paths():
    current_platform = system()
    base_path = 'Bin'
    platform_paths = {
        'Windows': {'7z': '7z.exe', 'fastgmad': 'fastgmad.exe'},
        'Linux': {'7z': '7z', 'fastgmad': 'fastgmad'},
        'Darwin': {'7z': '7z', 'fastgmad': 'fastgmad'}
    }

    if current_platform not in platform_paths:
        raise Exception(f"Unsupported platform: {current_platform}. Supported platforms are: Windows, Linux, macOS.")

    executable_path = {
        exe: path.join(base_path, current_platform, exe_name)
        for exe, exe_name in platform_paths[current_platform].items()
    }

    for exe, exe_path in executable_path.items():
        if not path.exists(exe_path):
            exe_path = input(f"Could not find {exe} at {exe_path}. Please provide the full path to the {exe} executable: ").strip()
            if not path.exists(exe_path):
                raise FileNotFoundError(f"Provided path for {exe} does not exist: {exe_path}")
            executable_path[exe] = exe_path

    return executable_path
