import platform
from os import path, scandir


def ask_for_absolute_paths():
    print("\nBundled executables were not found.")
    print("Please provide the absolute paths manually.\n")

    while True:
        seven_zip_path = input("Absolute path to 7z: ").strip().strip('"')
        fastgmad_path = input("Absolute path to fastgmad: ").strip().strip('"')

        missing = []

        if not path.isfile(seven_zip_path):
            missing.append("7z")

        if not path.isfile(fastgmad_path):
            missing.append("fastgmad")

        if missing:
            print(f"\nInvalid path(s): {', '.join(missing)}")
            print("Please check the paths and try again.\n")
            continue

        print("\nYou entered:")
        print(f"7z: {seven_zip_path}")
        print(f"fastgmad: {fastgmad_path}")

        confirm = (
            input("\nAre you sure these paths are correct? (Y/N): ").strip().lower()
        )

        if confirm == "y":
            return {"7z": seven_zip_path, "fastgmad": fastgmad_path}

        print("\nOkay, let's try again.\n")


def get_executable_paths():
    bin_dir = path.join("Bin", platform.system())
    system = platform.system()

    if system == "Windows":
        executables = {"7z": "7z.exe", "fastgmad": "fastgmad.exe"}
    else:
        executables = {"7z": "7z", "fastgmad": "fastgmad"}

    found = {}
    missing = []

    for name, filename in executables.items():
        full_path = path.join(bin_dir, filename)
        if path.exists(full_path):
            found[name] = full_path
        else:
            missing.append(filename)

    if missing:
        display_dir = bin_dir.replace("\\", "/")

        print(f"\nERROR: Required executables not found in {display_dir}/")
        print("Missing:", ", ".join(missing))

        if not path.exists(bin_dir):
            print(f"Directory '{display_dir}' does not exist")
        elif not path.isdir(bin_dir):
            print(f"'{display_dir}' is not a directory")
        else:
            try:
                files = [entry.name for entry in scandir(bin_dir) if entry.is_file()]
                if files:
                    print(f"Found: {', '.join(files)}")
                else:
                    print("Directory is empty")
            except PermissionError:
                print("Permission denied")

        return ask_for_absolute_paths()

    return found
