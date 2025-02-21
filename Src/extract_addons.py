from time import time
from uuid import uuid4
from shutil import move
from platform import system
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor
from os import path, scandir, rename, makedirs, rmdir, listdir, cpu_count
from utils import format_time

current_platform = system()
excluded_directories = ['Bin', 'Leftover', '_internal', 'Extracted-Addons']

def handle_error(file_name, error):
    if isinstance(error, FileNotFoundError):
        print(f"Error: File not found - {file_name}")
    elif isinstance(error, PermissionError):
        print(f"Error: Permission denied - {file_name}")
    elif isinstance(error, (EOFError, ValueError)):
        print(f"Error: Corrupt - {file_name}: {error}")
    else:
        print(f"Unexpected error processing {file_name}: {error}")

def get_executable_paths():
    base_path = 'Bin'
    platform_paths = {
        'Windows': {'7z': '7z.exe', 'fastgmad': 'fastgmad.exe'},
        'Linux': {'7z': '7z', 'fastgmad': 'fastgmad'},
        'Darwin': {'7z': '7z', 'fastgmad': 'fastgmad'}
    }

    if current_platform not in platform_paths:
        raise Exception(f"Unsupported platform: {current_platform}. Supported platforms are: Windows, Linux, macOS.")

    executable_path = {
        exe: path.join(base_path, current_platform, exe_name)
        for exe, exe_name in platform_paths[current_platform].items()
    }

    for exe, exe_path in executable_path.items():
        if not path.exists(exe_path):
            exe_path = input(f"Could not find {exe} at {exe_path}. Please provide the full path to the {exe} executable: ").strip()
            if not path.exists(exe_path):
                raise FileNotFoundError(f"Provided path for {exe} does not exist: {exe_path}")
            executable_path[exe] = exe_path

    return executable_path

def generate_unique_name(file_path):
    return path.join(path.dirname(file_path), uuid4().hex + path.splitext(file_path)[-1])

def find_files_with_extension(extension, start_dir):
    files = []
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                files.extend(find_files_with_extension(extension, entry.path))
            elif entry.is_file() and entry.name.endswith(extension):
                files.append(entry.path)
    except Exception as error:
        handle_error(start_dir, error)
    return files

def add_extension_to_files_without_format(start_dir):
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                add_extension_to_files_without_format(entry.path)
            elif entry.is_file() and '.' not in entry.name and entry.name not in ['VAE']:
                new_path = entry.path + '.gma'
                try:
                    rename(entry.path, new_path)
                except Exception as error:
                    handle_error(entry.path, error)
    except Exception as error:
        handle_error(start_dir, error)

def extract_bin_file(bin_file, seven_zip_path, addon_formats_count):
    print(f"Extracting {bin_file}...")
    try:
        run([seven_zip_path, 'x', bin_file, '-o' + path.dirname(bin_file)],
            stdout=DEVNULL, stderr=DEVNULL)
        addon_formats_count[".bin"] += 1
    except Exception as error:
        handle_error(bin_file, error)

def extract_gma_file(gma_file, fastgmad_path, addon_formats_count):
    addon_folder = path.join('Extracted-Addons', uuid4().hex)
    try:
        makedirs(addon_folder, exist_ok=True)
        print(f"Extracting {gma_file} to {addon_folder}...")
        run([fastgmad_path, 'extract', '-file', gma_file, '-out', addon_folder],
            stdout=DEVNULL, stderr=DEVNULL)
        addon_formats_count[".gma"] += 1
    except Exception as error:
        handle_error(gma_file, error)

def move_files_to_leftover(files, leftover_dir):
    try:
        makedirs(leftover_dir, exist_ok=True)
        for file in files:
            destination = path.join(leftover_dir, path.basename(file))
            if path.exists(destination):
                destination = generate_unique_name(destination)
            try:
                move(file, destination)
            except Exception as error:
                handle_error(file, error)
    except Exception as error:
        handle_error(leftover_dir, error)

def remove_empty_directories(start_dir):
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                remove_empty_directories(entry.path)
                try:
                    if not listdir(entry.path):
                        rmdir(entry.path)
                except Exception as error:
                    handle_error(entry.path, error)
    except Exception as error:
        handle_error(start_dir, error)

def main():
    start_time = time()
    try:
        exec_paths = get_executable_paths()
        seven_zip_path = exec_paths['7z']
        fastgmad_path = exec_paths['fastgmad']

        base_extract_dir = path.join('Extracted-Addons')
        makedirs(base_extract_dir, exist_ok=True)

        addon_formats_count = {".bin": 0, ".gma": 0}

        print("Searching for .bin files...")
        bin_files = find_files_with_extension('.bin', '.')
        if bin_files:
            workers = max(1, cpu_count())
            with ThreadPoolExecutor(max_workers=workers) as executor:
                executor.map(lambda f: extract_bin_file(f, seven_zip_path, addon_formats_count), bin_files)
            print(f"Found {len(bin_files)} .bin files.")
        else:
            print("No .bin files found.")

        print("Adding .gma extension to files without extensions...")
        add_extension_to_files_without_format('.')

        print("Searching for .gma files...")
        gma_files = find_files_with_extension('.gma', '.')
        if gma_files:
            workers = max(1, cpu_count())
            with ThreadPoolExecutor(max_workers=workers) as executor:
                executor.map(lambda f: extract_gma_file(f, fastgmad_path, addon_formats_count), gma_files)
            print(f"Found {len(gma_files)} .gma files.")
        else:
            print("No .gma files found.")

        print("Moving leftover files...")
        move_files_to_leftover(bin_files + gma_files, 'Leftover')

        print("Removing empty directories...")
        remove_empty_directories('.')
    except Exception as error:
        handle_error("main execution", error)
    finally:
        end_time = time()
        elapsed_time = end_time - start_time
        formatted_time = format_time(elapsed_time)

        print("\nSummary:")
        for addon_format, count in addon_formats_count.items():
            if count > 0:
                print(f"Total {addon_format} files processed: {count}")
        print(f"Total time taken: {formatted_time}")
