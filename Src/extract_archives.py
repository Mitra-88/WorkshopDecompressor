import sys
from time import time
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from os import path, makedirs, walk
from threading import Lock
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn

from utils import (
    format_time,
    unique_name,
    excluded_directories,
    remove_empty_directories,
)

archive_handlers = {
    ".zip": ZipFile,
    ".rar": RarFile,
    ".7z": SevenZipFile,
    ".tar": TarFile,
    ".gz": TarFile,
    ".xz": TarFile,
    ".bz2": TarFile,
}

archive_count = {ext: 0 for ext in archive_handlers.keys()}
count_lock = Lock()


def warn_user():
    print("\n⚠ WARNING ⚠")
    print("────────────────────────")
    print("Archive extraction modifies files.")
    print("Ensure files are not in use.")
    print("────────────────────────")

    while True:
        response = input("Continue? (y/n): ").lower().strip()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            print("Cancelled.")
            sys.exit(0)
        else:
            print("Invalid input.")


def extract_archive(archive_path):
    extension = path.splitext(archive_path)[1]
    archive_handler = archive_handlers.get(extension)

    base_output_dir = path.splitext(path.basename(archive_path))[0]
    output_dir = unique_name(base_output_dir)
    makedirs(output_dir, exist_ok=True)

    with archive_handler(archive_path, "r") as archive:
        archive.extractall(output_dir)

    leftover_folder = "Leftover"
    makedirs(leftover_folder, exist_ok=True)

    destination_path = path.join(leftover_folder, path.basename(archive_path))
    if path.exists(destination_path):
        destination_path = unique_name(destination_path)
    move(archive_path, destination_path)

    with count_lock:
        archive_count[extension] += 1


def process_archives():
    archives = []
    archive_extensions = {extension[1:] for extension in archive_handlers.keys()}

    for root, directories, files in walk("."):
        directories[:] = [d for d in directories if d not in excluded_directories]
        for file in files:
            if file.split(".")[-1] in archive_extensions:
                archives.append(path.join(root, file))
    return archives


def main():
    warn_user()
    start_time = time()

    print("\nScanning archives...")
    archives = process_archives()
    print(f"Found {len(archives)} archives")

    if not archives:
        print("No archives found in current directory.")
        return

    print("\nExtracting archives...")

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("processing", total=len(archives))
        for archive in archives:
            extract_archive(archive)
            progress.advance(task)

    print("\nCleaning up...")
    deleted_dirs_count = remove_empty_directories(".", excluded_directories)

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    total_processed = sum(archive_count.values())

    print("\n━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ COMPLETE")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Time: {formatted_time}")
    print(f"Processed: {total_processed}")
    print(f"Directories cleaned: {deleted_dirs_count}")
    print("━━━━━━━━━━━━━━━━━━━━━━")
