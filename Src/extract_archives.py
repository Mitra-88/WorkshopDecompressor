from time import time
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from os import path, makedirs, walk
from utils import format_time, unique_name, excluded_directories, remove_empty_directories

archive_handlers = {
    ".zip": ZipFile,
    ".rar": RarFile,
    ".7z": SevenZipFile,
    ".tar": TarFile,
    ".tar.gz": TarFile,
    ".tar.xz": TarFile,
    ".tar.bz2": TarFile,
    ".gz": TarFile,
    ".xz": TarFile,
    ".bz2": TarFile,
}

def get_archive_extension(filename):
    lower_name = filename.lower()

    for ext in [".tar.gz", ".tar.xz", ".tar.bz2"]:
        if lower_name.endswith(ext):
            return ext

    _, ext = path.splitext(filename)
    return ext.lower() if ext else None

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

def extract_archive(archive_path, archive_count):
    extension = get_archive_extension(archive_path)
    
    if not extension or extension not in archive_handlers:
        print(f"⚠️ Skipped: Unknown archive format")
        return

    archive_handler = archive_handlers[extension]

    base_name = path.basename(archive_path)
    if extension in [".tar.gz", ".tar.xz", ".tar.bz2"]:
        base_output_dir = base_name[:-(len(extension))]
    else:
        base_output_dir = path.splitext(base_name)[0]
    output_dir = unique_name(base_output_dir)
    makedirs(output_dir, exist_ok=True)

    with archive_handler(archive_path, 'r') as archive:
        archive.extractall(output_dir)

    leftover_folder = 'Leftover'
    makedirs(leftover_folder, exist_ok=True)

    destination_path = path.join(leftover_folder, base_name)
    if path.exists(destination_path):
        destination_path = unique_name(destination_path)
    move(archive_path, destination_path)

    if extension in archive_count:
        archive_count[extension] += 1
    else:
        archive_count[extension] = 1

def process_archives():
    archives = []

    for root, directories, files in walk('.'):
        directories[:] = [directory for directory in directories if directory not in excluded_directories]
        for file in files:
            ext = get_archive_extension(file)
            if ext and ext in archive_handlers:
                archives.append(path.join(root, file))
    
    return archives

def main():
    warn_user()
    start_time = time()

    print("┌────────────────────────────────────┐")
    print("│        Archive Extractor           │")
    print("└────────────────────────────────────┘")
    
    print("• Formats: ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.XZ, TAR.BZ2")
    
    archive_count = {
        ".zip": 0, ".rar": 0, ".7z": 0, ".tar": 0, 
        ".tar.gz": 0, ".tar.xz": 0, ".tar.bz2": 0,
        ".gz": 0, ".xz": 0, ".bz2": 0
    }
    
    print("• Scanning for archives...")
    archives = process_archives()
    print(f"• Found {len(archives)} total archives")

    found_counts = {ext: 0 for ext in archive_count.keys()}
    for archive in archives:
        ext = get_archive_extension(archive)
        if ext and ext in found_counts:
            found_counts[ext] += 1
    
    print("• Breakdown:")
    for ext, count in found_counts.items():
        if count > 0:
            print(f"  {ext.upper()}: {count}")

    if archives:
        print("• Extracting archives...")
        for i, archive in enumerate(archives, 1):
            ext = get_archive_extension(archive)
            print(f"• [{i}/{len(archives)}] {path.basename(archive)}")
            extract_archive(archive, archive_count)
        print("• Extraction complete")
    else:
        print("• No archives found")

    print("• Cleaning up...")
    deleted_dirs_count = remove_empty_directories('.')
    print(f"• Removed {deleted_dirs_count} empty directories")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n" + "─" * 45)
    print("COMPLETE")
    print("─" * 45)
    print(f"Time: {formatted_time}")
    print(f"Total: {len(archives)} archives")
    
    total_processed = 0
    for ext, count in archive_count.items():
        if count > 0:
            print(f"• {ext.upper()}: {count}")
            total_processed += count
    
    print(f"• Processed: {total_processed} files")
    print(f"• Archived: {len(archives)} files")
    print(f"• Directories cleaned: {deleted_dirs_count}")
    print("─" * 45)
