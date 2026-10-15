import logging
import os
import platform
import stat
import sys
from pathlib import Path
from subprocess import DEVNULL, run

import ui

logger = logging.getLogger("workshop.executables")


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _executables_for(system):
    return {
        "7z": "7z.exe" if system == "Windows" else "7z",
        "fastgmad": "fastgmad.exe" if system == "Windows" else "fastgmad",
    }


def prepare_executables(exec_paths):
    system = platform.system()
    if system not in ("Linux", "Darwin"):
        return

    for name, executable_path in exec_paths.items():
        try:
            path = Path(executable_path)
            os.chmod(path, path.stat().st_mode | stat.S_IEXEC)
        except OSError as exc:
            logger.warning(
                "Could not mark %s as executable. If it fails to run, check permissions. Reason: %s",
                name, exc
            )

        if system == "Darwin":
            try:
                run(
                    ["xattr", "-d", "com.apple.quarantine", str(path)],
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                )
            except OSError as exc:
                logger.warning(
                    "Could not clear the macOS quarantine flag on %s. If macOS refuses to open it, right-click it and choose Open. Reason: %s",
                    name, exc
                )


def locate_executables():
    system = platform.system()
    bin_dir = _get_base_dir() / "Bin" / system

    found = {}
    missing = []
    rows = []

    for name, filename in _executables_for(system).items():
        full_path = bin_dir / filename
        exists = full_path.is_file()

        rows.append(
            {
                "name": name,
                "path": str(full_path).replace("\\", "/"),
                "found": exists,
            }
        )

        if exists:
            found[name] = str(full_path)
        else:
            missing.append(name)

    return found, missing, rows, bin_dir


def ensure_executable_paths():
    found, missing, rows, bin_dir = locate_executables()

    ui.render_rule("Tool Setup")
    ui.render_tool_status(rows)

    if not missing:
        ui.render_spacer()
        ui.render_message(
            "Success! All required tools were found automatically.",
            "success",
        )
        ui.render_spacer()
        prepare_executables(found)
        return found

    ui.render_missing_tools_panel(missing)
    ui.render_directory_status(bin_dir)
    ui.render_spacer()

    manual_paths = ui.prompt_absolute_paths(missing)
    found.update(manual_paths)
    prepare_executables(found)

    return found
