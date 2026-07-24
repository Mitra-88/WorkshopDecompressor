import logging
from contextlib import nullcontext
from pathlib import Path
from shutil import move
from tarfile import open as TarFile
from time import time
from zipfile import ZipFile

import ui
from py7zr import SevenZipFile
from rarfile import RarFile
from utils import (excluded_directories, format_time, remove_empty_directories,
                   unique_name)

logger = logging.getLogger("workshop.archives")

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

ARCHIVE_WARNING_LINES = (
    "Archive extraction modifies files.",
    "Ensure files are not in use.",
)


def _null_stage(stage, description, total):
    return nullcontext(lambda: None)


def _log_archive_failure(outcome):
    name = outcome["file"].name
    reason = outcome.get("error") or "Unknown cause."
    logger.error("Could not extract %s. %s", name, reason)


def find_archives(start_dir="."):
    archives = []

    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        archives.extend(
            root / filename
            for filename in filenames
            if Path(filename).suffix.lower() in ARCHIVE_EXTENSIONS
        )

    return archives


def extract_archive(archive_path, leftover_dir):
    archive_path = Path(archive_path)

    try:
        extension = archive_path.suffix.lower()
        output_dir = unique_name(archive_path.stem)
        output_dir.mkdir(parents=True, exist_ok=True)

        with ARCHIVE_HANDLERS[extension](str(archive_path), "r") as archive:
            archive.extractall(output_dir)

        dest = leftover_dir / archive_path.name

        if dest.exists():
            dest = unique_name(dest)

        move(archive_path, dest)

        return {
            "file": archive_path,
            "success": True,
            "error": None,
        }

    except Exception:
        return {
            "file": archive_path,
            "success": False,
            "error": "Check that it is not corrupted, password-protected, or in use.",
        }


def run_archive_extraction(progress_factory=None):
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
            outcome = extract_archive(archive, leftover_dir)
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
    confirmed = ui.confirm_continue(
        "⚠ WARNING ⚠",
        ARCHIVE_WARNING_LINES,
        cancel_message="Cancelled.",
        invalid_message="Invalid input.",
    )

    if not confirmed:
        return

    summary = run_archive_extraction(ui.stage_progress)

    if summary.get("found", 0):
        ui.render_archive_summary(summary)
