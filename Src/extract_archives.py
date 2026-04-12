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
    print("⚠️  WARNING!")
    print("Please make sure files you want to process are not open in other programs.")
    print("These errors are NOT handled by this program.")
    print("Files with more than one dot in the name (like small.cats.png) won't work.")
    print("Only normal ones with one dot work (like cats.png).")

    while True:
        response = input("Do you want to continue? (y/n): ").lower().strip()
        if response == "y" or response == "yes":
            return True
        elif response == "n" or response == "no":
            print("Operation cancelled by user.")
            sys.exit(0)
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")


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
        directories[:] = [
            directory
            for directory in directories
            if directory not in excluded_directories
        ]
        for file in files:
            if file.split(".")[-1] in archive_extensions:
                archives.append(path.join(root, file))
    return archives


def main():
    warn_user()
    start_time = time()

    print("Archive Extractor")

    print("• Formats: ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.XZ, TAR.BZ2")

    print("• Scanning for archives...")
    archives = process_archives()
    print(f"• Found {len(archives)} total archives")

    if not archives:
        print("• No archives found")
        return

    print("• Extracting archives...")
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Extracting...", total=len(archives))
        for archive in archives:
            extract_archive(archive)
            progress.advance(task)

    print("• Extraction complete")
    print("• Cleaning up...")
    deleted_dirs_count = remove_empty_directories(".", excluded_directories)
    print(f"• Removed {deleted_dirs_count} empty directories")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n" + "─" * 45)
    print("COMPLETE")
    print("─" * 45)
    print(f"Time: {formatted_time}")
    total_processed = sum(archive_count.values())
    print(f"• Processed: {total_processed} files")
    for ext, count in archive_count.items():
        if count > 0:
            print(f"• {ext.upper()}: {count}")
    print(f"• Directories cleaned: {deleted_dirs_count}")
    print("─" * 45)
