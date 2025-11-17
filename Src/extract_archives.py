from time import time
from uuid import uuid4
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
    ".gz": TarFile,
    ".xz": TarFile,
    ".bz2": TarFile,
}

def extract_archive(archive_path, archive_count):
    extension = path.splitext(archive_path)[1]
    archive_handler = archive_handlers.get(extension)

    output_dir = uuid4().hex
    makedirs(output_dir, exist_ok=True)

    with archive_handler(archive_path, 'r') as archive:
        archive.extractall(output_dir)

    leftover_folder = 'Leftover'
    makedirs(leftover_folder, exist_ok=True)

    destination_path = path.join(leftover_folder, path.basename(archive_path))
    if path.exists(destination_path):
        destination_path = unique_name(destination_path)

    move(archive_path, destination_path)
    
    if extension in archive_count:
        archive_count[extension] += 1

def process_archives():
    archives = []
    archive_extensions = {extension[1:] for extension in archive_handlers.keys()}

    for root, directories, files in walk('.'):
        directories[:] = [directory for directory in directories if directory not in excluded_directories]
        for file in files:
            if file.split('.')[-1] in archive_extensions:
                archives.append(path.join(root, file))
    
    return archives

def main():
    start_time = time()

    print(">>> Starting Archive Extraction Process...")
    print(">>> Supported formats: ZIP, RAR, 7Z, TAR, GZ, XZ, BZ2")
    
    archive_count = {".zip": 0, ".rar": 0, ".7z": 0, ".tar": 0, ".gz": 0, ".xz": 0, ".bz2": 0}
    
    print(">>> Scanning for archive files...")
    archives = process_archives()
    print(f">>> Found {len(archives)} total archive files")

    found_counts = {ext: 0 for ext in archive_count.keys()}
    for archive in archives:
        ext = path.splitext(archive)[1]
        if ext in found_counts:
            found_counts[ext] += 1
    
    print(">>> Archive breakdown:")
    for ext, count in found_counts.items():
        if count > 0:
            print(f"    {ext.upper()}: {count} files")

    if archives:
        print(">>> Extracting archives...")
        for i, archive in enumerate(archives, 1):
            ext = path.splitext(archive)[1]
            print(f">>> Progress: {i}/{len(archives)} - Extracting {path.basename(archive)}")
            extract_archive(archive, archive_count)
        print(">>> Extraction completed successfully!")
    else:
        print(">>> No archive files found to process.")

    print(">>> Cleaning up empty directories...")
    deleted_dirs_count = remove_empty_directories('.')
    print(f">>> Removed {deleted_dirs_count} empty directories")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n" + "="*60)
    print("ARCHIVE EXTRACTION COMPLETE - SUMMARY")
    print("="*60)
    print(f"Total processing time: {formatted_time}")
    print(f"Total archives processed: {len(archives)}")
    print("\nDetailed breakdown:")
    
    total_processed = 0
    for ext, count in archive_count.items():
        if count > 0:
            print(f"  {ext.upper():6} : {count:3} files")
            total_processed += count
    
    print(f"\nSuccessfully processed: {total_processed} files")
    print(f"Moved to Leftover folder: {len(archives)} files")
    print(f"Empty directories removed: {deleted_dirs_count}")
    print("="*60)

if __name__ == "__main__":
    main()
