import sys
from time import time
from pathlib import Path
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn

from utils import (
    format_time,
    unique_name,
    excluded_directories,
    remove_empty_directories,
)

ARCHIVE_HANDLERS = {
    ".zip": ZipFile,
    ".rar": RarFile,
    ".7z": SevenZipFile,
    ".tar": TarFile,
    ".gz": TarFile,
    ".xz": TarFile,
    ".bz2": TarFile,
}

ARCHIVE_EXTENSIONS = frozenset(ARCHIVE_HANDLERS.keys())


def warn_user():
    print("\n⚠ WARNING ⚠")
    print("────────────────────────")
    print("Archive extraction modifies files.")
    print("Ensure files are not in use.")
    print("────────────────────────")

    while True:
        response = input("Continue? (y/n): ").lower().strip()
        if response in ("y", "yes"):
            return
        if response in ("n", "no"):
            print("Cancelled.")
            sys.exit(0)
        print("Invalid input.")


def extract_archive(archive_path, leftover_dir):
    extension = archive_path.suffix.lower()
    handler = ARCHIVE_HANDLERS[extension]

    output_dir = unique_name(archive_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)

    with handler(str(archive_path), "r") as archive:
        archive.extractall(output_dir)

    dest = leftover_dir / archive_path.name
    if dest.exists():
        dest = unique_name(dest)
    move(archive_path, dest)


def find_archives():
    archives = []
    for root, dirnames, filenames in Path(".").walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        for filename in filenames:
            if Path(filename).suffix.lower() in ARCHIVE_EXTENSIONS:
                archives.append(root / filename)
    return archives


def main():
    warn_user()
    start_time = time()

    print("\nScanning archives...")
    archives = find_archives()
    print(f"Found {len(archives)} archives")

    if not archives:
        print("No archives found in current directory.")
        return

    print("\nExtracting archives...")
    leftover_dir = Path("Leftover")
    leftover_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("processing", total=len(archives))
        for archive in archives:
            extract_archive(archive, leftover_dir)
            progress.advance(task)

    print("\nCleaning up...")
    deleted_dirs_count = remove_empty_directories(".")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ COMPLETE")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Time: {formatted_time}")
    print(f"Processed: {len(archives)}")
    print(f"Directories cleaned: {deleted_dirs_count}")
    print("━━━━━━━━━━━━━━━━━━━━━━")
