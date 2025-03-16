from time import time
from uuid import uuid4
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from os import path, makedirs, walk
from concurrent.futures import ProcessPoolExecutor
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

def extract_archive(archive_path):
    extension = path.splitext(archive_path)[1]
    archive_handler = archive_handlers[extension]

    try:
        unique_folder = uuid4().hex
        makedirs(unique_folder, exist_ok=True)

        with archive_handler(archive_path, 'r') as archive:
            archive.extractall(unique_folder)

        leftover_folder = 'Leftover'
        makedirs(leftover_folder, exist_ok=True)

        destination_path = path.join(leftover_folder, path.basename(archive_path))
        if path.exists(destination_path):
            destination_path = path.join(leftover_folder, f"{path.basename(archive_path)}-{uuid4().hex}{extension}")

        move(archive_path, destination_path)
        print(f"Processed and moved: {archive_path}")
        
        return (extension, True)

    except FileNotFoundError:
        print(f"Error: File not found - {archive_path}")
    except PermissionError:
        print(f"Error: Permission denied - {archive_path}")
    except (EOFError, ValueError) as archive_error:
        print(f"Error: Corrupt or unsupported archive - {archive_path}: {archive_error}")
    except Exception as error:
        print(f"Unexpected error processing {archive_path}: {str(error)}")
    
    return (extension, False)

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
    
    archive_count = {extension: 0 for extension in archive_handlers.keys()}
    
    with ProcessPoolExecutor() as executor:
        results = executor.map(extract_archive, archives)
    
    for extension, success in results:
        if success:
            archive_count[extension] += 1
    
    print("\nSummary:")
    for extension, count in archive_count.items():
        if count > 0:
            print(f"Total {extension} files processed: {count}")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print(f"Total time taken: {formatted_time}")
