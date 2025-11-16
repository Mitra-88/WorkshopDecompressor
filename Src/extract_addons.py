from time import time
from uuid import uuid4
from shutil import move
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor
from os import path, scandir, rename, makedirs, cpu_count
from utils import format_time, get_executable_paths, unique_name, excluded_directories, delete_empty_dirs

def find_files_with_extension(extension, start_dir):
    files = []
    for entry in scandir(start_dir):
        if entry.is_dir() and entry.name not in excluded_directories:
            files.extend(find_files_with_extension(extension, entry.path))
        elif entry.is_file() and entry.name.endswith(extension):
            files.append(entry.path)
    return files

def add_extension_to_files_without_format(start_dir):
    for entry in scandir(start_dir):
        if entry.is_dir() and entry.name not in excluded_directories:
            add_extension_to_files_without_format(entry.path)
        elif entry.is_file() and '.' not in entry.name and entry.name not in ['Workshop Decompressor']:
            new_path = entry.path + '.gma'
            rename(entry.path, new_path)

def extract_bin_file(bin_file, seven_zip_path, addon_formats_count):
    extract_directory = path.join(path.dirname(bin_file), uuid4().hex)
    run([seven_zip_path, 'x', bin_file, '-o' + extract_directory],
        stdout=DEVNULL, stderr=DEVNULL)
    addon_formats_count[".bin"] += 1

def extract_gma_file(gma_file, fastgmad_path, addon_formats_count):
    addon_folder = path.join('Extracted-Addons', uuid4().hex)
    makedirs(addon_folder, exist_ok=True)
    run([fastgmad_path, 'extract', '-file', gma_file, '-out', addon_folder],
        stdout=DEVNULL, stderr=DEVNULL)
    addon_formats_count[".gma"] += 1

def move_files_to_leftover(files, leftover_dir):
    makedirs(leftover_dir, exist_ok=True)
    for file in files:
        destination = path.join(leftover_dir, path.basename(file))
        if path.exists(destination):
            destination = unique_name(destination)
        move(file, destination)

def main():
    start_time = time()
    addon_formats_count = {".bin": 0, ".gma": 0}
    
    exec_paths = get_executable_paths()
    seven_zip_path = exec_paths['7z']
    fastgmad_path = exec_paths['fastgmad']

    base_extract_dir = path.join('Extracted-Addons')
    makedirs(base_extract_dir, exist_ok=True)

    bin_files = find_files_with_extension('.bin', '.')
    if bin_files:
        workers = max(1, cpu_count() - 2)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(lambda f: extract_bin_file(f, seven_zip_path, addon_formats_count), bin_files)

    add_extension_to_files_without_format('.')

    gma_files = find_files_with_extension('.gma', '.')
    if gma_files:
        workers = max(1, cpu_count() - 2)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(lambda f: extract_gma_file(f, fastgmad_path, addon_formats_count), gma_files)

    move_files_to_leftover(bin_files + gma_files, 'Leftover')

    delete_empty_dirs('.')

    end_time = time()
    elapsed_time = end_time - start_time
    formatted_time = format_time(elapsed_time)

if __name__ == "__main__":
    main()
