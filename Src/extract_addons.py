from logging import getLogger, basicConfig, INFO
from time import time
from uuid import uuid4
from shutil import move
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor
from os import path, scandir, rename, makedirs, cpu_count
from utils import format_time, get_executable_paths, unique_name, handle_error, excluded_directories, remove_empty_directories

basicConfig(level=INFO, format="[%(asctime)s %(levelname)s]: %(message)s", datefmt="%H:%M:%S")
logger = getLogger("vae_main")

def find_files_with_extension(extension, start_dir):
    files = []
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                files.extend(find_files_with_extension(extension, entry.path))
            elif entry.is_file() and entry.name.endswith(extension):
                files.append(entry.path)
    except Exception as error:
        handle_error(start_dir, error)
    return files

def add_extension_to_files_without_format(start_dir):
    try:
        for entry in scandir(start_dir):
            if entry.is_dir() and entry.name not in excluded_directories:
                add_extension_to_files_without_format(entry.path)
            elif entry.is_file() and '.' not in entry.name and entry.name not in ['VAE']:
                new_path = entry.path + '.gma'
                try:
                    rename(entry.path, new_path)
                except Exception as error:
                    handle_error(entry.path, error)
    except Exception as error:
        handle_error(start_dir, error)

def extract_bin_file(bin_file, seven_zip_path, addon_formats_count):
    logger.info("Extracting %s...", bin_file)
    try:
        extract_directory = path.join(path.dirname(bin_file), uuid4().hex)
        run([seven_zip_path, 'x', bin_file, '-o' + extract_directory],
            stdout=DEVNULL, stderr=DEVNULL)
        addon_formats_count[".bin"] += 1
    except Exception as error:
        handle_error(bin_file, error)

def extract_gma_file(gma_file, fastgmad_path, addon_formats_count):
    addon_folder = path.join('Extracted-Addons', uuid4().hex)
    try:
        makedirs(addon_folder, exist_ok=True)
        logger.info("Extracting %s to %s...", gma_file, addon_folder)
        run([fastgmad_path, 'extract', '-file', gma_file, '-out', addon_folder],
            stdout=DEVNULL, stderr=DEVNULL)
        addon_formats_count[".gma"] += 1
    except Exception as error:
        handle_error(gma_file, error)

def move_files_to_leftover(files, leftover_dir):
    try:
        makedirs(leftover_dir, exist_ok=True)
        for file in files:
            destination = path.join(leftover_dir, path.basename(file))
            if path.exists(destination):
                destination = unique_name(destination)
            try:
                move(file, destination)
            except Exception as error:
                handle_error(file, error)
    except Exception as error:
        handle_error(leftover_dir, error)

def main():
    start_time = time()
    addon_formats_count = {".bin": 0, ".gma": 0}
    try:
        exec_paths = get_executable_paths()
        seven_zip_path = exec_paths['7z']
        fastgmad_path = exec_paths['fastgmad']

        base_extract_dir = path.join('Extracted-Addons')
        makedirs(base_extract_dir, exist_ok=True)

        logger.info("Searching for .bin files...")
        bin_files = find_files_with_extension('.bin', '.')
        if bin_files:
            workers = max(1, cpu_count())
            with ThreadPoolExecutor(max_workers=workers) as executor:
                executor.map(lambda f: extract_bin_file(f, seven_zip_path, addon_formats_count), bin_files)
            logger.info("Found %d .bin files.", len(bin_files))
        else:
            logger.warning("No .bin files found.")

        logger.info("Adding .gma extension to files without extensions...")
        add_extension_to_files_without_format('.')

        logger.info("Searching for .gma files...")
        gma_files = find_files_with_extension('.gma', '.')
        if gma_files:
            workers = max(1, cpu_count())
            with ThreadPoolExecutor(max_workers=workers) as executor:
                executor.map(lambda f: extract_gma_file(f, fastgmad_path, addon_formats_count), gma_files)
            logger.info("Found %d .gma files.", len(gma_files))
        else:
            logger.warning("No .gma files found.")

        logger.info("Moving leftover files...")
        move_files_to_leftover(bin_files + gma_files, 'Leftover')

        logger.info("Removing empty directories...")
        remove_empty_directories('.')
    except Exception as error:
        handle_error("main execution", error)
    finally:
        end_time = time()
        elapsed_time = end_time - start_time
        formatted_time = format_time(elapsed_time)

        logger.info("Summary:")
        for addon_format, count in addon_formats_count.items():
            logger.info("Total %s files processed: %d", addon_format, count)
        logger.info("Total time taken: %s", formatted_time)
