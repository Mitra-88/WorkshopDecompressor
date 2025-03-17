from time import time
from uuid import uuid4
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from os import path, makedirs, walk
from utils import format_time

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

    try:
        makedirs(uuid4().hex, exist_ok=True)

        with archive_handler(archive_path, 'r') as archive:
            archive.extractall(uuid4().hex)

        leftover_folder = 'Leftover'
        if not path.exists(leftover_folder):
            makedirs(leftover_folder)

        destination_path = path.join(leftover_folder, path.basename(archive_path))
        if path.exists(destination_path):
            destination_path = path.join(leftover_folder, f"{path.splitext(path.basename(archive_path))[0]}-{uuid4().hex}{extension}")

        move(archive_path, destination_path)
        print(f"Processed and moved: {archive_path}")
        
        if extension in archive_count:
            archive_count[extension] += 1

    except FileNotFoundError:
        print(f"Error: File not found - {archive_path.name}")
    except PermissionError:
        print(f"Error: Permission denied - {archive_path.name}")
    except (EOFError, ValueError) as archive_error:
        print(f"Error: Corrupt or unsupported archive - {archive_path.name}: {archive_error}")
    except Exception as error:
        print(f"Unexpected error processing {archive_path.name}: {str(error)}")

def process_archives():
    excluded_directories = {'Bin', 'Leftover', '_internal', 'Extracted-Addons'}
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

    archives = process_archives()
    if not archives:
        print("No archives found.")
        return

    archive_count = {".zip": 0, ".rar": 0, ".7z": 0, ".tar": 0, ".gz": 0, ".xz": 0, ".bz2": 0,}

    for archive in archives:
        extract_archive(archive, archive_count)

    print("\nSummary:")
    for extension, count in archive_count.items():
        if count > 0:
            print(f"Total {extension} files processed: {count}")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print(f"Total time taken: {formatted_time}")
