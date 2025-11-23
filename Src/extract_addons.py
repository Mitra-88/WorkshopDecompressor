from time import time
from shutil import move
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import path, scandir, rename, makedirs, cpu_count
from threading import Lock
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from utils import format_time, get_executable_paths, unique_name, excluded_directories, remove_empty_directories

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
        elif entry.is_file() and '.' not in entry.name and entry.name not in ['Workshop Decompressor']:
            new_path = entry.path + '.gma'
            rename(entry.path, new_path)
            renamed_count += 1
    return renamed_count

def extract_bin_file(bin_file, seven_zip_path):
    base_folder = path.join(path.dirname(bin_file), "Extracted-Bin")
    extract_directory = unique_name(base_folder)
    makedirs(extract_directory, exist_ok=True)
    run([seven_zip_path, 'x', bin_file, '-o' + extract_directory],
        stdout=DEVNULL, stderr=DEVNULL)
    with count_lock:
        addon_formats_count[".bin"] += 1

def extract_gma_file(gma_file, fastgmad_path):
    base_folder = path.join("Extracted-Addons", "Addon")
    addon_folder = unique_name(base_folder)
    makedirs(addon_folder, exist_ok=True)
    run([fastgmad_path, 'extract', '-file', gma_file, '-out', addon_folder],
        stdout=DEVNULL, stderr=DEVNULL)
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
    lines = [
        "⚠️  WARNING!",
        "Please close ALL programs using:",
        "• .gma addon files",
        "• .bin files",
        "If these files are in use, errors may occur.",
        "These errors are NOT handled by this script."
    ]
    width = max(len(line) for line in lines) + 4
    print("┌" + "─" * width + "┐")
    for line in lines:
        print("│ " + line.ljust(width - 2) + " │")
    print("└" + "─" * width + "┘")

    confirmation = ""
    while confirmation.lower() != "i understand":
        confirmation = input("Type 'I understand' to continue: ").strip()

def main():
    warn_user()
    start_time = time()

    print("┌───────────────────────────────────────┐")
    print("│        Workshop Decompressor          │")
    print("└───────────────────────────────────────┘")
    
    print("• Setting up environment...")
    exec_paths = get_executable_paths()
    seven_zip_path = exec_paths['7z']
    fastgmad_path = exec_paths['fastgmad']

    base_extract_dir = path.join('Extracted-Addons')
    makedirs(base_extract_dir, exist_ok=True)

    print("• Scanning for .bin files...")
    bin_files = find_files_with_extension('.bin', '.')
    print(f"• Found {len(bin_files)} .bin files")

    if bin_files:
        workers = max(1, cpu_count() - 2)
        print(f"• Extracting {len(bin_files)} files with {workers} workers...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("Extracting .bin files", total=len(bin_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(extract_bin_file, f, seven_zip_path) for f in bin_files]
                for f in as_completed(futures):
                    progress.advance(task)

    print("• Checking for files without extensions...")
    renamed_count = add_extension_to_files_without_format('.')
    if renamed_count > 0:
        print(f"• Added .gma extension to {renamed_count} files")

    print("• Scanning for .gma files...")
    gma_files = find_files_with_extension('.gma', '.')
    print(f"• Found {len(gma_files)} .gma files")

    if gma_files:
        workers = max(1, cpu_count() - 2)
        print(f"• Extracting {len(gma_files)} files with {workers} workers...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("Extracting .gma files", total=len(gma_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(extract_gma_file, f, fastgmad_path) for f in gma_files]
                for f in as_completed(futures):
                    progress.advance(task)

    print("• Moving processed files...")
    all_processed_files = bin_files + gma_files
    moved_count = move_files_to_leftover(all_processed_files, 'Leftover')
    print(f"• Moved {moved_count} files to Leftover")

    print("• Cleaning empty directories...")
    deleted_dirs_count = remove_empty_directories('.', excluded_directories)
    print(f"• Removed {deleted_dirs_count} empty directories")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n" + "─" * 40)
    print("SUMMARY")
    print("─" * 40)
    print(f"Time: {formatted_time}")
    print(f"• .bin files: {addon_formats_count['.bin']}")
    print(f"• .gma files: {addon_formats_count['.gma']}")
    print(f"• Files renamed: {renamed_count}")
    print(f"• Output: {base_extract_dir}")
    print(f"• Archived: {moved_count}")
    print("─" * 40)
