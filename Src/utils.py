import platform
from os import scandir, rmdir, path

excluded_directories = {"Bin", "Leftover", "_internal", "Extracted-Addons"}

app_version = f"v2.5.0 (12d8bac)"
build_date = "2025-11-18 (Tuesday, November 18, 2025)"

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
    
    return {exe: path.join(base_dir, platform_name, exe_name) 
            for exe, exe_name in executables[platform_name].items()}

def unique_name(file_path):
    if not path.exists(file_path):
        return file_path
        
    base, extension = path.splitext(file_path)
    counter = 1
    
    while True:
        new_name = f"{base}-{counter}{extension}"
        if not path.exists(new_name):
            print(f"Detected duplicate file. Renaming to: {new_name}")
            return new_name
        counter += 1

def remove_empty_directories(path, excluded=()):
    deleted_count = 0
    with scandir(path) as entries:
        for entry in entries:
            if entry.is_dir() and entry.name not in excluded:
                deleted_count += remove_empty_directories(entry.path, excluded)
    with scandir(path) as entries:
        if not any(True for _ in entries):
            rmdir(path)
            deleted_count += 1
    return deleted_count
