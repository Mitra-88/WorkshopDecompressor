import sys
import platform
from os import path, scandir

def get_executable_paths():
    bin_dir = path.join('Bin', platform.system())
    system = platform.system()

    if system == 'Windows':
        executables = {'7z': '7z.exe', 'fastgmad': 'fastgmad.exe'}
    else:
        executables = {'7z': '7z', 'fastgmad': 'fastgmad'}

    found = {}
    missing = []

    for name, filename in executables.items():
        full_path = path.join(bin_dir, filename)
        if path.exists(full_path):
            found[name] = full_path
        else:
            missing.append(filename)

    if missing:
        display_dir = bin_dir.replace('\\', '/')

        print(f"\nERROR: Required executables not found in {display_dir}/")
        print("Missing:", ', '.join(missing))
        
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
                    print(f"Directory is empty")
            except PermissionError:
                print(f"Permission denied")

        while input("\nType 'I understand' to exit: ").strip().lower() != "i understand":
            pass

        sys.exit(0)

    return found
