import sys
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_system_info, app_version, build_date
from py7zr import __version__ as py7zr_version
from rarfile import __version__ as rarfile_version
from PyInstaller import __version__ as pyinstaller_version

def display_info():
    print(
        f"{'=' * 40}\n"
        f"Workshop Decompressor {app_version}.\n"
        f"{'=' * 40}\n"
    )

def display_build_info():
    separator = "=" * 75
    info = (
        f"Build Information:\n"
        f"{separator}\n"
        f"Program         : Workshop Decompressor {app_version}\n"
        f"Build Date      : {build_date}\n"
        f"Operating System: {get_system_info()}\n"
        f"Dependencies    : PyInstaller {pyinstaller_version}, Py7zr {py7zr_version}, RarFile {rarfile_version}, 7-Zip 25.01\n"
        f"{separator}"
    )
    print(info)

def display_menu():
    print(
        "Select an option:\n"
        "1. Extract addons\n"
        "2. Extract archives\n"
        "3. Help\n"
        "4. Build Info\n"
        "5. Exit\n"
    )

def display_help():
    print(
        "\n=== HELP MENU ===\n"
        "1. Extract Addons      - Extracts GMA and BIN addon files.\n"
        "2. Extract Archives    - Extracts archive files (ZIP, RAR, 7Z, TAR, TAR.XZ, TAR.GZ, TAR.BZ2).\n"
        "3. Help                - Displays this help menu.\n"
        "4. Build Info          - Shows detailed build information about the program.\n"
        "5. Exit                - Closes the application.\n"
    )

def handle_choice(user_input):
    def invalid_choice():
        print("Invalid choice: Please select 1-5")

    options = {
        "1": extract_addons,
        "2": extract_archives,
        "3": display_help,
        "4": display_build_info,
        "5": sys.exit
    }
    
    action = options.get(user_input, invalid_choice)
    action()

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
