from uuid import uuid4
from os import path, rmdir, listdir, scandir
from platform import system, architecture, win32_ver, win32_edition, freedesktop_os_release, mac_ver, machine

excluded_directories = {'Bin', 'Leftover', '_internal', 'Extracted-Addons'}

vae_version = f"v2.4.5 (3be74ee)"
build_date = "2025-07-11 (Friday, July 11, 2025)"

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

def unique_name(file_path):
    base, extension = path.splitext(file_path)
    new_name = f"{base}-{uuid4().hex[:7]}{extension}"
    print(f"Detected duplicate file. Renaming to: {new_name}")
    return new_name

def remove_empty_directories(start_dir):
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                remove_empty_directories(entry.path)
                try:
                    if not listdir(entry.path):
                        rmdir(entry.path)
                except Exception as error:
                    handle_error(entry.path, error)
    except Exception as error:
        handle_error(start_dir, error)

def handle_error(file_name, error):
    if isinstance(error, FileNotFoundError):
        print(f"Error: File not found - {file_name}")
    elif isinstance(error, PermissionError):
        print(f"Error: Permission denied - {file_name}")
    elif isinstance(error, (EOFError, ValueError)):
        print(f"Error: Corrupt - {file_name}: {error}")
    else:
        print(f"Unexpected error processing {file_name}: {error}")
