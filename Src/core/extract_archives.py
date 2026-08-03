import logging
import tarfile
from contextlib import nullcontext
from pathlib import Path
from shutil import move
from subprocess import DEVNULL, run
from time import time
from zipfile import ZipFile

import ui
from get_executable import ensure_executable_paths
from rarfile import RarFile
from utils import (excluded_directories, format_time, remove_empty_directories,
                   unique_name)

logger = logging.getLogger("workshop.archives")

ARCHIVE_HANDLERS = {
    ".zip": ZipFile,
    ".rar": RarFile,
    ".tar": tarfile.open,
    ".tar.gz": tarfile.open,
    ".tgz": tarfile.open,
    ".tar.bz2": tarfile.open,
    ".tar.xz": tarfile.open,
}

SEVEN_ZIP_EXTENSIONS = frozenset({".7z"})
ARCHIVE_EXTENSIONS = frozenset(ARCHIVE_HANDLERS.keys()) | SEVEN_ZIP_EXTENSIONS

ARCHIVE_WARNING_LINES = (
    "Archive extraction modifies files.",
    "Ensure files are not in use.",
)

_warning_confirmed = False


def _null_stage(stage, description, total):
    return nullcontext(lambda: None)


def _log_archive_failure(outcome):
    name = outcome["file"].name
    reason = outcome.get("error") or "Unknown cause."
    logger.error("Could not extract %s. %s", name, reason)


def _get_archive_extension(filename):
    path = Path(filename)
    name_lower = path.name.lower()

    for compound_ext in [".tar.gz", ".tar.bz2", ".tar.xz", ".tgz"]:
        if name_lower.endswith(compound_ext):
            return compound_ext

    return path.suffix.lower()


def find_archives(start_dir="."):
    archives = []

    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        for filename in filenames:
            ext = _get_archive_extension(filename)
            if ext in ARCHIVE_EXTENSIONS:
                archives.append(Path(root) / filename)

    return archives


def extract_archive(archive_path, leftover_dir, seven_zip_path):
    archive_path = Path(archive_path)

    try:
        extension = _get_archive_extension(archive_path.name)
        output_dir = unique_name(archive_path.stem)
        output_dir.mkdir(parents=True, exist_ok=True)

        if extension in SEVEN_ZIP_EXTENSIONS:
            result = run(
                [seven_zip_path, "x", str(archive_path), f"-o{output_dir}", "-y"],
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
            if result.returncode != 0:
                raise RuntimeError(f"7-Zip exited with code {result.returncode}")
        
        elif extension in {".zip", ".rar"}:
            handler = ARCHIVE_HANDLERS[extension]
            with handler(str(archive_path), "r") as archive:
                archive.extractall(output_dir)
        
        else:
            try:
                with tarfile.open(str(archive_path), "r") as archive:
                    archive.extractall(output_dir, filter='data')
            except tarfile.TarError as e:
                error_msg = str(e)
                if "truncated" in error_msg.lower():
                    raise RuntimeError(f"Invalid tar archive: file appears truncated")
                elif "not a" in error_msg.lower():
                    raise RuntimeError("File is not a valid tar archive")
                else:
                    raise RuntimeError(f"Tar extraction error: {error_msg}")

        dest = leftover_dir / archive_path.name

        if dest.exists():
            dest = unique_name(dest)

        move(archive_path, dest)

        return {
            "file": archive_path,
            "success": True,
            "error": None,
        }

    except Exception as e:
        error_msg = str(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: Unknown error"
        
        return {
            "file": archive_path,
            "success": False,
            "error": error_msg,
        }


def run_archive_extraction(progress_factory=None, seven_zip_path=None):
    progress_factory = progress_factory or _null_stage

    logger.info("Scanning archives...")
    archives = find_archives()
    logger.info("Found %d archives", len(archives))

    if not archives:
        logger.info("No archives found in current directory.")
        return {
            "elapsed_seconds": 0.0,
            "elapsed": format_time(0.0),
            "found": 0,
            "processed": 0,
            "directories_cleaned": 0,
            "failures": [],
        }

    leftover_dir = Path("Leftover")
    leftover_dir.mkdir(exist_ok=True)

    start_time = time()
    processed = 0
    failures = []

    logger.info("Extracting archives...")

    with progress_factory("archive", "Extracting archives", len(archives)) as advance:
        for archive in archives:
            outcome = extract_archive(archive, leftover_dir, seven_zip_path)
            processed += 1

            if not outcome["success"]:
                failures.append(outcome)
                _log_archive_failure(outcome)

            advance()

    logger.info("Cleaning up...")
    deleted_dirs_count = remove_empty_directories(".")

    elapsed_time = time() - start_time

    summary = {
        "elapsed_seconds": elapsed_time,
        "elapsed": format_time(elapsed_time),
        "found": len(archives),
        "processed": processed,
        "directories_cleaned": deleted_dirs_count,
        "failures": failures,
    }

    logger.info("Archive extraction completed in %s", summary["elapsed"])
    return summary


def main():
    global _warning_confirmed

    if not _warning_confirmed:
        confirmed = ui.confirm_continue(
            "⚠ WARNING ⚠",
            ARCHIVE_WARNING_LINES,
            cancel_message="Cancelled.",
            invalid_message="Invalid input.",
        )

        if not confirmed:
            return

        _warning_confirmed = True

    exec_paths = ensure_executable_paths()
    summary = run_archive_extraction(ui.stage_progress, exec_paths["7z"])

    if summary.get("found", 0):
        ui.render_archive_summary(summary)