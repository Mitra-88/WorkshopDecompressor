import sys
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_system_info, workshopdecompressor_version, build_date
from py7zr import __version__ as py7zr_version
from rarfile import __version__ as rarfile_version
from PyInstaller import __version__ as pyinstaller_version

def display_info():
    print(
        f"\n{'=' * 45}\n"
        f"Workshop Decompressor {workshopdecompressor_version}.\n"
        f"{'=' * 45}\n"
    )

def display_build_info():
    print(
        f"\nBuild Information:\n"
        f"{'-' * 75}\n"
        f"Program: Workshop Decompressor {workshopdecompressor_version}\n"
        f"Build Date: {build_date}\n"
        f"Operating System: {get_system_info()}\n"
        f"Dependencies:\n"
        f"  • PyInstaller: {pyinstaller_version}\n"
        f"  • Py7zr: {py7zr_version}\n"
        f"  • RarFile: {rarfile_version}\n"
        f"  • 7-zip: 25.01\n"
        f"{'-' * 75}\n"
    )

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
        "\nHelp:\n"
        "1. Extract addons - For GMA and BIN files.\n"
        "2. Extract archives - Extracts archive formats (ZIP/RAR/7Z/TAR/TAR.XZ/TAR.GZ/TAR.BZ2).\n"
        "3. Help - Displays this info.\n"
        "4. Build Info - Shows detailed build information.\n"
        "5. Exit - Closes the program.\n"
    )

def handle_choice(user_input):
    options = {
        "1": extract_addons,
        "2": extract_archives,
        "3": display_help,
        "4": display_build_info,
        "5": lambda: sys.exit(0)
    }
    
    action = options.get(user_input, lambda: print("Invalid choice: Please select 1-5"))
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
