import sys
from uuid import uuid4
from datetime import datetime
from platform import system, architecture, win32_ver, win32_edition, freedesktop_os_release, mac_ver, machine
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives

version = f"v2.4.0 ({uuid4().hex[:7]})"
build_date = datetime.now().strftime("%Y-%m-%d (%A, %B %d, %Y)")
rarfile_version = "4.2"
py7zr_version = "0.22.0"
pyinstaller_version = "6.11.1"
seven_zip_version = "24.09"

def display_info():
    system_info = get_os_info()
    print(
        f"{'=' * 75}\n"
        f"Vermeil's Addon Extractor {version}, {system_info}.\n"
        f"Build Date: {build_date}.\n"
        f"Build Info: Pyinstaller {pyinstaller_version}, Py7zr {py7zr_version}, "
        f"RarFile {rarfile_version}, 7-zip {seven_zip_version}.\n"
        f"{'=' * 75}\n"
    )

def display_menu():
    print(
        "Select an option:\n"
        "1. Extract addons\n"
        "2. Extract archives\n"
        "3. Help\n"
        "4. Exit\n"
    )

def display_help():
    print(
        "\nHelp:\n"
        "1. Extract addons - For GMA and BIN files.\n"
        "2. Extract archives - Extracts archive formats (ZIP, RAR, 7Z, TAR, TAR.XZ, TAR.GZ, TAR.BZ2). Mainly for 3rd party.\n"
        "3. Help - Displays this info.\n"
        "4. Exit - Closes the program.\n"
    )

def handle_choice(choice):
    options = {
        "1": extract_addons,
        "2": extract_archives,
        "3": display_help,
        "4": sys.exit
    }

    if choice in options:
        options[choice]()
    else:
        print("Invalid choice. Please enter a number from 1 to 4.")

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

def main():
    try:
        display_info()
        while True:
            display_menu()
            choice = input("Enter your choice (1-4): ").strip()
            handle_choice(choice)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
