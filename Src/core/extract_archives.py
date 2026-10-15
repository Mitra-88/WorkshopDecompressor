import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from pathlib import Path
from shutil import move
from time import time

import ui
from get_executable import ensure_executable_paths
from utils import (
    excluded_directories,
    extraction_workers,
    format_time,
    remove_empty_directories,
    run_sevenzip_extraction,
    unique_name,
)

logger = logging.getLogger("workshop.archives")

MAX_WORKERS = 10
workers = extraction_workers(MAX_WORKERS)

ARCHIVE_EXTENSIONS = frozenset(
    {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".tar.gz",
        ".tar.xz",
        ".tar.bz2",
    }
)

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

    for compound_ext in [".tar.gz", ".tar.xz", ".tar.bz2"]:
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
        stem = archive_path.name[: -len(extension)] or "archive"
        output_dir = unique_name(stem)
        output_dir.mkdir(parents=True, exist_ok=True)

        extracted, returncode, message = run_sevenzip_extraction(
            seven_zip_path, archive_path, output_dir
        )

        if not extracted:
            raise RuntimeError(f"7-Zip failed: {message}")

        warning = None
        if returncode >= 2:
            warning = f"7-Zip reported: {message}"
            logger.warning("Extracted %s, but %s", archive_path.name, message)

        dest = leftover_dir / archive_path.name

        if dest.exists():
            dest = unique_name(dest)

        move(archive_path, dest)

        return {
            "file": archive_path,
            "success": True,
            "error": None,
            "warning": warning,
        }

    except Exception as e:  # noqa: BLE001
        error_msg = str(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: Unknown error"

        return {
            "file": archive_path,
            "success": False,
            "error": error_msg,
        }


def _process_parallel_archives(
    files,
    stage,
    description,
    worker,
    leftover_dir,
    tool_path,
    progress_factory,
):
    processed = 0
    failures = []
    warnings = []

    with (
        progress_factory(stage, description, len(files)) as advance,
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(worker, file, leftover_dir, tool_path): file
            for file in files
        }

        try:
            for future in as_completed(futures):
                source = futures[future]

                try:
                    outcome = future.result()
                except Exception as exc:  # noqa: BLE001
                    outcome = {
                        "file": Path(source),
                        "success": False,
                        "error": f"Unexpected problem: {exc}",
                    }
                    logger.debug("Archive extraction exception: %s", exc)

                processed += 1

                if not outcome["success"]:
                    failures.append(outcome)
                    _log_archive_failure(outcome)
                elif outcome.get("warning"):
                    warnings.append(
                        {"file": Path(source), "message": outcome["warning"]}
                    )

                advance()
        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    return processed, failures, warnings


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
            "warnings": [],
            "failures": [],
        }

    leftover_dir = Path("Leftover")
    try:
        leftover_dir.mkdir(exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Cannot write to the current folder ({exc}). "
            "Move this program to a folder you can write to and run it again."
        ) from exc

    start_time = time()

    logger.info("Extracting %d archives using %d cores...", len(archives), workers)
    processed, failures, warnings = _process_parallel_archives(
        archives,
        "archive",
        "Extracting archives",
        extract_archive,
        leftover_dir,
        seven_zip_path,
        progress_factory,
    )

    logger.info("Cleaning up...")
    deleted_dirs_count = remove_empty_directories(".")

    elapsed_time = time() - start_time

    summary = {
        "elapsed_seconds": elapsed_time,
        "elapsed": format_time(elapsed_time),
        "found": len(archives),
        "processed": processed,
        "directories_cleaned": deleted_dirs_count,
        "warnings": warnings,
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

    ui.render_archive_summary(summary)
