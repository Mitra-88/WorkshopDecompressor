import logging
import os
import platform
import stat
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from pathlib import Path
from shutil import move
from subprocess import DEVNULL, run
from time import time

import ui
from get_executable import ensure_executable_paths
from utils import (excluded_directories, format_time, remove_empty_directories,
                   unique_name)

logger = logging.getLogger("workshop.addons")

MAX_WORKERS = 32
system_cores = os.cpu_count() or 2
workers = min(MAX_WORKERS, max(1, system_cores - 2))

ADDON_WARNING_LINES = (
    "Please close ALL programs using:",
    "• .gma addon files",
    "• .bin files",
    "If these files are in use, errors may occur.",
    "These errors are NOT handled by this program.",
)

_warning_confirmed = False


def _null_stage(stage, description, total):
    return nullcontext(lambda: None)


def _outcome(file, success, returncode=None, error=None):
    return {
        "file": file,
        "success": success,
        "returncode": returncode,
        "error": error,
    }


def _log_extraction_failure(outcome):
    name = outcome["file"].name
    reason = outcome.get("error") or "Unknown cause."
    code = outcome.get("returncode")

    if code is None:
        logger.error("Could not extract %s. %s", name, reason)
    else:
        logger.error("Could not extract %s (code %s). %s", name, code, reason)


def find_files_with_extension(extension, start_dir="."):
    files = []

    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]
        files.extend(
            root / filename
            for filename in filenames
            if filename.lower().endswith(extension)
        )

    return files


def add_extension_to_files_without_format(start_dir="."):
    renamed = 0

    for root, dirnames, filenames in Path(start_dir).walk():
        dirnames[:] = [d for d in dirnames if d not in excluded_directories]

        for filename in filenames:
            if "." in filename or filename == "WorkshopDecompressor":
                continue

            src = root / filename

            try:
                src.rename(src.with_suffix(".gma"))
                renamed += 1
            except OSError as exc:
                logger.error(
                    "Could not rename %s. Check that the file is not open or locked.",
                    filename,
                )
                logger.debug("Rename failure: %s", exc)

    return renamed


def extract_bin_file(bin_file, seven_zip_path):
    bin_file = Path(bin_file)

    try:
        extract_dir = unique_name(bin_file.parent / "Extracted-Bin")
        extract_dir.mkdir(parents=True, exist_ok=True)

        result = run(
            [seven_zip_path, "x", str(bin_file), f"-o{extract_dir}", "-y"],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )

        if result.returncode >= 2 and not any(extract_dir.iterdir()):
            return _outcome(
                bin_file,
                False,
                result.returncode,
                "7-Zip could not extract this file. "
                "Close programs using it or verify the file is valid.",
            )

        return _outcome(bin_file, True, result.returncode)

    except OSError:
        return _outcome(
            bin_file,
            False,
            error="Could not run 7-Zip. "
            "Check that the executable exists and is not blocked.",
        )


def extract_gma_file(gma_file, fastgmad_path):
    gma_file = Path(gma_file)

    try:
        addon_dir = unique_name(Path("Extracted-Addons") / "Addon")
        addon_dir.mkdir(parents=True, exist_ok=True)

        result = run(
            [
                fastgmad_path,
                "extract",
                "-file",
                str(gma_file),
                "-out",
                str(addon_dir),
            ],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )

        if result.returncode != 0:
            return _outcome(
                gma_file,
                False,
                result.returncode,
                "fastgmad could not extract this file. "
                "Close programs using it or verify the file is valid.",
            )

        return _outcome(gma_file, True, result.returncode)

    except OSError:
        return _outcome(
            gma_file,
            False,
            error="Could not run fastgmad. "
            "Check that the executable exists and is not blocked.",
        )


def move_files_to_leftover(files, leftover_dir):
    leftover = Path(leftover_dir)
    leftover.mkdir(parents=True, exist_ok=True)

    moved = 0

    for file in files:
        file = Path(file)

        if not file.exists():
            continue

        dest = leftover / file.name

        dest = unique_name(dest)

        try:
            move(file, dest)
            moved += 1
        except OSError as exc:
            logger.error(
                "Could not move %s. Check that the file is not open and you have permission.",
                file.name,
            )
            logger.debug("Move failure: %s", exc)

    return moved


def prepare_executables(exec_paths):
    if platform.system() not in ("Linux", "Darwin"):
        return

    for name, executable_path in exec_paths.items():
        try:
            path = Path(executable_path)
            os.chmod(path, path.stat().st_mode | stat.S_IEXEC)
        except OSError as exc:
            logger.warning(
                "Could not mark %s as executable. If it fails to run, check permissions.",
                name,
            )
            logger.debug("chmod failure: %s", exc)


def _process_parallel(
    files,
    stage,
    description,
    worker,
    tool_path,
    progress_factory,
    debug_label,
):
    processed = 0
    failures = []

    with progress_factory(stage, description, len(files)) as advance:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(worker, file, tool_path): file for file in files}

            for future in as_completed(futures):
                source = futures[future]

                try:
                    outcome = future.result()
                except Exception as exc:
                    outcome = _outcome(
                        Path(source),
                        False,
                        error="Unexpected problem while extracting. "
                        "Check file access and permissions.",
                    )
                    logger.debug("%s extraction exception: %s", debug_label, exc)

                processed += 1

                if not outcome["success"]:
                    failures.append(outcome)
                    _log_extraction_failure(outcome)

                advance()

    return processed, failures


def run_addon_extraction(exec_paths, progress_factory=None):
    progress_factory = progress_factory or _null_stage

    missing_tools = [tool for tool in ("7z", "fastgmad") if tool not in exec_paths]
    if missing_tools:
        raise RuntimeError("Missing required tool paths: " + ", ".join(missing_tools))

    start_time = time()

    logger.info("[1/5] Setting up environment...")
    prepare_executables(exec_paths)
    Path("Extracted-Addons").mkdir(exist_ok=True)

    logger.info("[2/5] Scanning for .bin files...")
    bin_files = find_files_with_extension(".bin")
    logger.info("Found %d .bin files", len(bin_files))

    bin_processed = 0
    bin_failures = []

    if bin_files:
        logger.info("[3/5] Extracting .bin files using %d workers...", workers)
        bin_processed, bin_failures = _process_parallel(
            bin_files,
            "bin",
            "Processing .bin files",
            extract_bin_file,
            exec_paths["7z"],
            progress_factory,
            "BIN",
        )
    else:
        logger.info("No .bin files found.")

    logger.info("[4/5] Fixing missing extensions...")
    renamed_count = add_extension_to_files_without_format()

    if renamed_count:
        logger.info("Fixed %d files", renamed_count)

    logger.info("[5/5] Scanning .gma files...")
    gma_files = find_files_with_extension(".gma")
    logger.info("Found %d .gma files", len(gma_files))

    gma_processed = 0
    gma_failures = []

    if gma_files:
        logger.info("Extracting .gma files using %d workers...", workers)
        gma_processed, gma_failures = _process_parallel(
            gma_files,
            "gma",
            "Processing .gma files",
            extract_gma_file,
            exec_paths["fastgmad"],
            progress_factory,
            "GMA",
        )
    else:
        logger.info("No .gma files found.")

    logger.info("Moving processed files...")
    moved_count = move_files_to_leftover(bin_files + gma_files, Path("Leftover"))

    logger.info("Cleaning empty directories...")
    remove_empty_directories(".")

    elapsed_time = time() - start_time

    summary = {
        "elapsed_seconds": elapsed_time,
        "elapsed": format_time(elapsed_time),
        "bin_found": len(bin_files),
        "gma_found": len(gma_files),
        "bin_processed": bin_processed,
        "gma_processed": gma_processed,
        "renamed": renamed_count,
        "moved": moved_count,
        "failures": bin_failures + gma_failures,
    }

    logger.info("Addon extraction completed in %s", summary["elapsed"])
    return summary


def main():
    global _warning_confirmed

    if not _warning_confirmed:
        if not ui.confirm_continue("⚠ WARNING ⚠", ADDON_WARNING_LINES):
            return
        _warning_confirmed = True

    exec_paths = ensure_executable_paths()
    summary = run_addon_extraction(exec_paths, ui.stage_progress)
    ui.render_addon_summary(summary)
