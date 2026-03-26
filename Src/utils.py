import platform
from uuid import uuid4
from datetime import datetime
from os import scandir, rmdir, path

excluded_directories = {"Bin", "Leftover", "_internal", "Extracted-Addons"}

app_version = f"v2.6.2 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d)")

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

def get_executable_paths():
    bin_dir = path.join('Bin', platform.system())
    files = {'7z': '7z.exe' if platform.system() == 'Windows' else '7z',
             'fastgmad': 'fastgmad.exe' if platform.system() == 'Windows' else 'fastgmad'}
    result, missing = {}, []

    for key, fname in files.items():
        full = path.join(bin_dir, fname)
        if not path.exists(full):
            missing.append(full)
        result[key] = full

    if missing:
        lines = [
            "⚠️  WARNING: Some required executables are missing!",
            "Possible reasons:",
            " • You forgot to copy/move the 'Bin' folder into the program's directory",
            " • An antivirus or other program removed some files",
            "Please make sure the 'Bin' folder exists and contains:"
        ]
        lines += [f" • {m}" for m in missing]
        lines.append("The program may not work correctly until this is fixed.")
        
        width = max(len(line) for line in lines) + 4
        print("┌" + "─" * width + "┐")
        for line in lines:
            print("│ " + line.ljust(width - 2) + " │")
        print("└" + "─" * width + "┘\n")
        
        confirmation = ""
        while confirmation.lower() != "i understand":
            confirmation = input("Type 'I understand' to continue: ").strip()

    return result

def unique_name(file_path):
    base, extension = path.splitext(file_path)

    while True:
        new_name = f"{base}-{uuid4().hex[:7]}{extension}"
        if not path.exists(new_name):
            print(f"Detected duplicate file/folder. Renaming to: {new_name}")
            return new_name

def remove_empty_directories(directory, excluded=excluded_directories):
    deleted_count = 0
    dir_name = path.basename(directory)
    if dir_name in excluded:
        return 0
    try:
        with scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir():
                    if entry.name not in excluded:
                        deleted_count += remove_empty_directories(entry.path, excluded)
    except PermissionError:
        return deleted_count
    except FileNotFoundError:
        return deleted_count
    try:
        with scandir(directory) as entries:
            is_empty = not any(True for _ in entries)
    except (OSError, PermissionError, FileNotFoundError):
        return deleted_count

    if is_empty and dir_name not in excluded:
        try:
            rmdir(directory)
            deleted_count += 1
        except (OSError, PermissionError, FileNotFoundError):
            pass

    return deleted_count
