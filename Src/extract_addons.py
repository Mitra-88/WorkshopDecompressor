import os
import stat
import sys
from time import time
from pathlib import Path
from shutil import move
from subprocess import run, DEVNULL
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)

from utils import (
    format_time,
    unique_name,
    excluded_directories,
    remove_empty_directories,
)
from get_executable import get_executable_paths

MAX_WORKERS = 32
system_cores = os.cpu_count() or 2
workers = min(MAX_WORKERS, max(1, system_cores - 2))


def find_files_with_extension(extension, start_dir="."):
    result = []
    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        for filename in filenames:
            if filename.lower().endswith(extension):
                result.append(str(root / filename))
    return result


def add_extension_to_files_without_format(start_dir="."):
    renamed = 0
    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        for filename in filenames:
            if "." not in filename and filename != "WorkshopDecompressor":
                src = root / filename
                src.rename(src.with_suffix(".gma"))
                renamed += 1
    return renamed


def extract_bin_file(bin_file, seven_zip_path):
    extract_dir = unique_name(Path(bin_file).parent / "Extracted-Bin")
    extract_dir.mkdir(parents=True, exist_ok=True)

    result = run(
        [seven_zip_path, "x", bin_file, f"-o{extract_dir}", "-y"],
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    if result.returncode >= 2 and not any(extract_dir.iterdir()):
        print(f"\nFailed to extract {Path(bin_file).name} (Error Code: {result.returncode})")


def extract_gma_file(gma_file, fastgmad_path):
    addon_dir = unique_name(Path("Extracted-Addons") / "Addon")
    addon_dir.mkdir(parents=True, exist_ok=True)

    result = run(
        [fastgmad_path, "extract", "-file", gma_file, "-out", str(addon_dir)],
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    if result.returncode != 0:
        print(f"\nFailed to extract {Path(gma_file).name} (Error Code: {result.returncode})")


def move_files_to_leftover(files, leftover_dir):
    leftover = Path(leftover_dir)
    leftover.mkdir(parents=True, exist_ok=True)
    moved = 0
    for file in files:
        dest = leftover / Path(file).name
        if dest.exists():
            dest = unique_name(dest)
        move(file, dest)
        moved += 1
    return moved


def warn_user():
    print("\n ⚠ WARNING ⚠")
    print("────────────────────────")
    print("Please close ALL programs using:")
    print("• .gma addon files")
    print("• .bin files")
    print("If these files are in use, errors may occur.")
    print("These errors are NOT handled by this program.")
    print("────────────────────────")

    while True:
        response = input("Continue? (y/n): ").lower().strip()
        if response in ("y", "yes"):
            return
        if response in ("n", "no"):
            print("Operation cancelled.")
            sys.exit(0)
        print("Invalid input. Please enter 'y' or 'n'.")


def main():
    warn_user()
    start_time = time()

    print("\n[1/5] Setting up environment...")

    exec_paths = get_executable_paths()
    seven_zip_path = exec_paths["7z"]
    fastgmad_path = exec_paths["fastgmad"]

    for exe in (seven_zip_path, fastgmad_path):
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)

    Path("Extracted-Addons").mkdir(exist_ok=True)

    print("\n[2/5] Scanning for .bin files...")
    bin_files = find_files_with_extension(".bin")
    print(f"Found {len(bin_files)} .bin files")

    bin_count = 0
    if bin_files:
        print(f"\n[3/5] Extracting .bin files ({workers} workers)...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]Processing .bin files"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("bin", total=len(bin_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(extract_bin_file, f, seven_zip_path): f
                    for f in bin_files
                }
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        future.result()
                        bin_count += 1
                    except OSError as exc:
                        print(f"\nError processing {Path(file_path).name}: {exc}")
                    progress.advance(task)
    else:
        print("No .bin files found.")

    print("\n[4/5] Fixing missing extensions...")
    renamed_count = add_extension_to_files_without_format()
    if renamed_count:
        print(f"Fixed {renamed_count} files")

    print("\n[5/5] Scanning .gma files...")
    gma_files = find_files_with_extension(".gma")
    print(f"Found {len(gma_files)} .gma files")

    gma_count = 0
    if gma_files:

        with Progress(
            SpinnerColumn(),
            TextColumn("[green]Processing .gma files"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("gma", total=len(gma_files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(extract_gma_file, f, fastgmad_path): f
                    for f in gma_files
                }
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        future.result()
                        gma_count += 1
                    except OSError as exc:
                        print(f"\nError processing {Path(file_path).name}: {exc}")
                    progress.advance(task)
    else:
        print("No .gma files found.")

    print("\nMoving processed files...")
    moved_count = move_files_to_leftover(bin_files + gma_files, "Leftover")

    print("Cleaning empty directories...")
    _ = remove_empty_directories(".")

    elapsed_time = time() - start_time
    formatted_time = format_time(elapsed_time)

    print("\n━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ PROCESS COMPLETE")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Time: {formatted_time}")
    print(f".bin files: {bin_count}")
    print(f".gma files: {gma_count}")
    print(f"Renamed: {renamed_count}")
    print("Output: Extracted-Addons")
    print(f"Moved: {moved_count}")
    print("━━━━━━━━━━━━━━━━━━━━━━")
