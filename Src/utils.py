import os
import platform
from uuid import uuid4
from datetime import datetime

excluded_directories = {"Bin", "Leftover", "_internal", "Extracted-Addons"}

workshopdecompressor_version = f"v2.5.0 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d, %Y)")

def format_time(seconds):
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    
    parts = []
    if h: parts.append(f"{h:.0f}h")
    if m: parts.append(f"{m:.0f}m")
    if s or not parts: parts.append(f"{s:.3f}s")
    
    return ' '.join(parts)

def normalize_architecture(arch):
    mapping = {
        "x86_64": "64-Bit",
        "amd64": "AMD64",
        "arm64": "ARM64",
        "aarch64": "ARM64",
        "64bit": "64-Bit",
    }
    return mapping.get(arch.lower(), arch)

def get_system_info():
    system = platform.system()
    arch = normalize_architecture(platform.machine())
    if system == "Windows":
        edition = platform.win32_edition()
        release = platform.release()
        version = platform.version()
        return f"{system} {release} {edition} (Build {version}) {arch}".strip()
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

def get_executable_paths():
    platform_name = platform.system()
    base_dir = 'Bin'
    executables = {
        'Windows': {'7z': '7z.exe', 'fastgmad': 'fastgmad.exe'},
        'Linux': {'7z': '7z', 'fastgmad': 'fastgmad'},
        'Darwin': {'7z': '7z', 'fastgmad': 'fastgmad'}
    }
    
    return {exe: os.path.join(base_dir, platform_name, exe_name) 
            for exe, exe_name in executables[platform_name].items()}

def unique_name(file_path):
    if not os.path.exists(file_path):
        return file_path
        
    base, extension = os.path.splitext(file_path)
    counter = 1
    
    while True:
        new_name = f"{base}-{counter}{extension}"
        if not os.path.exists(new_name):
            print(f"Detected duplicate file. Renaming to: {new_name}")
            return new_name
        counter += 1

def delete_empty_dirs(root, excluded_directories=None):
    if excluded_directories is None:
        excluded_directories = set()
    
    excluded_directories = set(os.path.normpath(path) for path in excluded_directories)
    
    for dirpath, dirnames, _ in os.walk(root, topdown=False):
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            if (not os.listdir(full_path) and 
                os.path.normpath(full_path) not in excluded_directories):
                os.rmdir(full_path)
