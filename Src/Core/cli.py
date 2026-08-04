import logging
import sys

import ui
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from PyInstaller import __version__ as pyinstaller_version
from rarfile import __version__ as rarfile_version
from utils import app_version, build_date, get_system_info

logger = logging.getLogger("workshop.cli")

MENU_ITEMS = (
    ("1", "Extract Addons", "Extract GMA and BIN addon files"),
    ("2", "Extract Archives", "Extract ZIP, RAR, 7Z, TAR files"),
    ("3", "Help", "Show help menu"),
    ("4", "Build Info", "Show system and build info"),
    ("5", "Exit", "Close program"),
)


def _build_info():
    return {
        "Program": f"Workshop Decompressor {app_version}",
        "Build Date": build_date,
        "Operating System": get_system_info(),
        "Dependencies": (
            f"PyInstaller {pyinstaller_version}, "
            f"RarFile {rarfile_version}, "
            f"Rich 15.0.0, "
            "7-Zip 26.02"
        ),
    }


def handle_choice(choice):
    match choice:
        case "1":
            extract_addons()
        case "2":
            extract_archives()
        case "3":
            ui.render_help(MENU_ITEMS)
        case "4":
            ui.render_build_info(_build_info())
        case "5":
            ui.render_message("Exiting... Goodbye!", "success")
            sys.exit(0)

    ui.pause()


def main():
    ui.configure_logging()
    ui.set_cli_title(f"Workshop Decompressor {app_version}")

    try:
        ui.render_banner(app_version)

        while True:
            ui.render_spacer()
            ui.render_menu(MENU_ITEMS)

            choice = ui.prompt_choice(("1", "2", "3", "4", "5"))

            ui.render_spacer()

            try:
                handle_choice(choice)
            except SystemExit:
                raise
            except Exception:
                logger.error(
                    "Something failed unexpectedly. "
                    "Check that files are accessible and required tools are available."
                )
                ui.pause()

    except (KeyboardInterrupt, EOFError):
        ui.render_spacer()
        ui.render_message("Force quitting...", "error")
        sys.exit(0)


if __name__ == "__main__":
    main()
