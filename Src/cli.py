import sys
from uuid import uuid4
from datetime import datetime
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_os_info

version = f"v2.4.2 ({uuid4().hex[:7]})"
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
