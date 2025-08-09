from time import time
from uuid import uuid4
from shutil import move
from zipfile import ZipFile
from rarfile import RarFile
from py7zr import SevenZipFile
from tarfile import open as TarFile
from os import path, makedirs, walk
from logging import getLogger, basicConfig, INFO
from utils import format_time, unique_name, excluded_directories, remove_empty_directories

basicConfig(level=INFO, format="[%(asctime)s %(levelname)s]: %(message)s", datefmt="%H:%M:%S")
logger = getLogger("archive_processor")

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
        logger.info("Processed and moved: %s", archive_path)
        
        if extension in archive_count:
            archive_count[extension] += 1

    except FileNotFoundError:
        logger.error("Error: File not found - %s", archive_path)
    except PermissionError:
        logger.error("Error: Permission denied - %s", archive_path)
    except (EOFError, ValueError) as archive_error:
        logger.error("Error: Corrupt or unsupported archive - %s: %s", archive_path, archive_error)
    except Exception as error:
        logger.error("Unexpected error processing %s: %s", archive_path, str(error))

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

    archive_count = {".zip": 0, ".rar": 0, ".7z": 0, ".tar": 0, ".gz": 0, ".xz": 0, ".bz2": 0}
    archives = process_archives()
    if not archives:
        logger.warning("No archives found.")
    else:
        for archive in archives:
            extract_archive(archive, archive_count)

    logger.info("Removing empty directories...")
    remove_empty_directories('.')

    logger.info("Summary:")
    for extension, count in archive_count.items():
        logger.info("Total %s files processed: %d", extension, count)

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)
    logger.info("Total time taken: %s", formatted_time)

if __name__ == "__main__":
    main()
