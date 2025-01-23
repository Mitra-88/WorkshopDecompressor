from platform import system, architecture, win32_ver, win32_edition, freedesktop_os_release, mac_ver, machine

def format_time(seconds):
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds:.3f}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:.3f}s"
    else:
        return f"{seconds:.3f}s"

def normalize_architecture(arch: str) -> str:
    arch_map = {
        "x86_64": "64-Bit",
        "64bit": "64-Bit",
        "arm64": "ARM64",
        "aarch64": "ARM64",
    }
    return arch_map.get(arch, arch)

def get_windows_info() -> str:
    try:
        win_version, _, _, _ = win32_ver()
        win_edition = win32_edition()
        arch = normalize_architecture(architecture()[0])
        return f"Windows {win_version} {win_edition} {arch}"
    except Exception as e:
        return f"Windows (Error: {e})"

def get_linux_info() -> str:
    try:
        distro_info = freedesktop_os_release()
        pretty_name = distro_info.get("PRETTY_NAME", "Linux")
        version = distro_info.get("VERSION", "")
        version_id = distro_info.get("VERSION_ID", "")
        arch = normalize_architecture(architecture()[0])

        if pretty_name:
            return f"{pretty_name} {arch}"
        elif version:
            return f"{version} {arch}"
        else:
            name = distro_info.get("NAME", "Linux")
            if version_id:
                return f"{name} {version_id} {arch}"
            else:
                return f"{name} {arch}"

    except OSError:
        return f"Linux {normalize_architecture(architecture()[0])}"
    except Exception as e:
        return f"Linux (Error: {e})"

def get_macos_info() -> str:
    try:
        mac_version = mac_ver()[0]
        arch = normalize_architecture(machine())
        return f"macOS {mac_version} {arch}"
    except Exception as e:
        return f"macOS (Error: {e})"

def get_os_info() -> str:
    sys = system()

    if sys == "Windows":
        return get_windows_info()
    elif sys == "Linux":
        return get_linux_info()
    elif sys == "Darwin":
        return get_macos_info()
    else:
        return f"Unknown OS (System: {sys})"
