import os
import sys
import stat
from time import time
from shutil import move
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import path, scandir, rename, makedirs, cpu_count
from threading import Lock
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)

from utils import (
    format_time,
    unique_name,
    excluded_directories,
    remove_empty_directories,
)
from get_executable import get_executable_paths

count_lock = Lock()
addon_formats_count = {".bin": 0, ".gma": 0}


def find_files_with_extension(extension, start_dir):
    files = []
    for entry in scandir(start_dir):
        if entry.is_dir() and entry.name not in excluded_directories:
            files.extend(find_files_with_extension(extension, entry.path))
        elif entry.is_file() and entry.name.endswith(extension):
            files.append(entry.path)
    return files


def add_extension_to_files_without_format(start_dir):
    renamed_count = 0
    for entry in scandir(start_dir):
        if entry.is_dir() and entry.name not in excluded_directories:
            renamed_count += add_extension_to_files_without_format(entry.path)
        elif (
            entry.is_file()
            and "." not in entry.name
            and entry.name not in ["WorkshopDecompressor"]
        ):
            new_path = entry.path + ".gma"
            rename(entry.path, new_path)
            renamed_count += 1
    return renamed_count


def extract_bin_file(bin_file, seven_zip_path):
    base_folder = path.join(path.dirname(bin_file), "Extracted-Bin")
    extract_directory = unique_name(base_folder)
    makedirs(extract_directory, exist_ok=True)
    
    result = run(
        [seven_zip_path, "x", bin_file, f"-o{extract_directory}", "-y"], stdout=DEVNULL, stderr=DEVNULL
    )

    if result.returncode >= 2:
        if not os.listdir(extract_directory):
            print(f"\nFailed to extract {path.basename(bin_file)} (Error Code: {result.returncode})")
    
    with count_lock:
        addon_formats_count[".bin"] += 1


def extract_gma_file(gma_file, fastgmad_path):
    base_folder = path.join("Extracted-Addons", "Addon")
    addon_folder = unique_name(base_folder)
    makedirs(addon_folder, exist_ok=True)
    
    result = run(
        [fastgmad_path, "extract", "-file", gma_file, "-out", addon_folder], stdout=DEVNULL, stderr=DEVNULL
    )

    if result.returncode != 0:
        print(f"\nFailed to extract {path.basename(gma_file)} (Error Code: {result.returncode})")
        
    with count_lock:
        addon_formats_count[".gma"] += 1


def move_files_to_leftover(files, leftover_dir):
    makedirs(leftover_dir, exist_ok=True)
    moved_count = 0
    for file in files:
        destination = path.join(leftover_dir, path.basename(file))
        if path.exists(destination):
            destination = unique_name(destination)
        move(file, destination)
        moved_count += 1
    return moved_count


def warn_user():
    print("\n ⚠ WARNING ⚠")
    print("────────────────────────")
    print("Please close ALL programs using:")
    print("• .gma addon files")
    print("• .bin files")
    print("If these files are in use, errors may occur.")
    print("These errors are NOT handled by this program.")
    print("────────────────────────")

    while True:
        response = input("Continue? (y/n): ").lower().strip()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            print("Operation cancelled.")
            sys.exit(0)
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def main():
    warn_user()
    start_time = time()

    print("\n[1/5] Setting up environment...")

    exec_paths = get_executable_paths()
    seven_zip_path = exec_paths["7z"]
    fastgmad_path = exec_paths["fastgmad"]

    os.chmod(seven_zip_path, os.stat(seven_zip_path).st_mode | stat.S_IEXEC)
    os.chmod(fastgmad_path, os.stat(fastgmad_path).st_mode | stat.S_IEXEC)

    base_extract_dir = path.join("Extracted-Addons")
    makedirs(base_extract_dir, exist_ok=True)

    print("\n[2/5] Scanning for .bin files...")
    bin_files = find_files_with_extension(".bin", ".")
    print(f"Found {len(bin_files)} .bin files")

    if not bin_files:
        print("No .bin files found.")
    else:
        workers = max(1, cpu_count() - 2)
        print(f"\n[3/5] Extracting .bin files ({workers} workers)...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]Processing .bin files"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("bin", total=len(bin_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(extract_bin_file, f, seven_zip_path)
                    for f in bin_files
                ]
                for _ in as_completed(futures):
                    progress.advance(task)

    print("\n[4/5] Fixing missing extensions...")
    renamed_count = add_extension_to_files_without_format(".")
    if renamed_count:
        print(f"Fixed {renamed_count} files")

    print("\n[5/5] Scanning .gma files...")
    gma_files = find_files_with_extension(".gma", ".")
    print(f"Found {len(gma_files)} .gma files")

    if not gma_files:
        print("No .gma files found.")
    else:
        workers = max(1, cpu_count() - 2)

        with Progress(
            SpinnerColumn(),
            TextColumn("[green]Processing .gma files"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("gma", total=len(gma_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(extract_gma_file, f, fastgmad_path)
                    for f in gma_files
                ]
                for _ in as_completed(futures):
                    progress.advance(task)

    print("\nMoving processed files...")
    all_processed_files = bin_files + gma_files
    moved_count = move_files_to_leftover(all_processed_files, "Leftover")

    print("Cleaning empty directories...")
    deleted_dirs_count = remove_empty_directories(".", excluded_directories)

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ PROCESS COMPLETE")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Time: {formatted_time}")
    print(f".bin files: {addon_formats_count['.bin']}")
    print(f".gma files: {addon_formats_count['.gma']}")
    print(f"Renamed: {renamed_count}")
    print(f"Output: {base_extract_dir}")
    print(f"Moved: {moved_count}")
    print("━━━━━━━━━━━━━━━━━━━━━━")
