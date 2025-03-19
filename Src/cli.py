import sys
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_os_info, vae_version, build_date
from py7zr import __version__ as py7zr_version
from rarfile import __version__ as rarfile_version
from PyInstaller import __version__ as pyinstaller_version

def display_info():
    print(
        f"\n{'=' * 75}\n"
        f"Vermeil's Addon Extractor {vae_version}, {get_os_info()}.\n"
        f"Build Date: {build_date}.\n"
        f"Build Info: Pyinstaller {pyinstaller_version}, Py7zr {py7zr_version}, "
        f"RarFile {rarfile_version}, 7-zip 24.09.\n"
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
        "2. Extract archives - Extracts archive formats (ZIP/RAR/7Z/TAR/TAR.XZ/TAR.GZ/TAR.BZ2).\n"
        "3. Help - Displays this info.\n"
        "4. Exit - Closes the program.\n"
    )

def handle_choice(user_input):
    options = {
        "1": extract_addons,
        "2": extract_archives,
        "3": display_help,
        "4": lambda: sys.exit(0)
    }
    
    action = options.get(user_input, lambda: print("Invalid choice: Please select 1-4"))
    action()

def main():
    try:
        display_info()
        while True:
            display_menu()
            handle_choice(input("Enter your choice (1-4): ").strip())
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
