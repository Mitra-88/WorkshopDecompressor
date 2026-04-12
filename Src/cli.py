import os
import sys
import platform
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_system_info, app_version, build_date
from py7zr import __version__ as py7zr_version
from rarfile import __version__ as rarfile_version
from PyInstaller import __version__ as pyinstaller_version


def set_cli_title():
    title = f"Workshop Decompressor {app_version}"
    system = platform.system()

    if system == "Windows":
        os.system(f"title {title}")
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()


set_cli_title()


def display_info():
    print(f"{'=' * 40}\nWorkshop Decompressor {app_version}.\n{'=' * 40}\n")


def display_build_info():
    info = (
        f"\nBuild Information:\n"
        f"Program         : Workshop Decompressor {app_version}\n"
        f"Build Date      : {build_date}\n"
        f"Operating System: {get_system_info()}\n"
        f"Dependencies    : PyInstaller {pyinstaller_version}, Py7zr {py7zr_version}, RarFile {rarfile_version}, Rich 15.0.0, 7-Zip 26.00\n"
    )
    print(info)


def display_menu():
    print(
        "\nMAIN MENU\n"
        "────────────────────\n"
        "1. Extract addons\n"
        "2. Extract archives\n"
        "3. Help\n"
        "4. Build Info\n"
        "5. Exit\n"
        "────────────────────\n"
    )


def display_help():
    print(
        "\nHELP MENU\n"
        "────────────────────────\n"
        "1. Extract Addons   - Extract GMA and BIN addon files\n"
        "2. Extract Archives - Extract ZIP, RAR, 7Z, TAR files\n"
        "3. Help             - Show this menu\n"
        "4. Build Info      - Show system + build info\n"
        "5. Exit             - Close program\n"
        "────────────────────────\n"
    )


def pause():
    input("\nPress ENTER to return to menu...")


def handle_choice(user_input):
    def invalid_choice():
        print("Invalid choice: Please select 1-5")

    options = {
        "1": extract_addons,
        "2": extract_archives,
        "3": display_help,
        "4": display_build_info,
        "5": sys.exit,
    }

    action = options.get(user_input, invalid_choice)
    action()

    if user_input != "5":
        pause()


def main():
    try:
        display_info()
        while True:
            display_menu()
            handle_choice(input("Enter your choice (1-5): ").strip())
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
