import logging
import sys

import ui
from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from update_check import start as start_update_check
from update_check import take_notice
from utils import app_version, build_date, get_system_info, tool_versions

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
        "Dependencies": tool_versions,
    }


def handle_choice(choice):
    match choice:
        case "1":
            extract_addons()
        case "2":
            extract_archives()
        case "3":
            ui.render_help()
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
        start_update_check()
        ui.render_banner(app_version)

        while True:
            notice = take_notice()

            if notice:
                ui.render_update_notice(*notice)

            ui.render_spacer()
            ui.render_menu(MENU_ITEMS)

            choice = ui.prompt_choice(("1", "2", "3", "4", "5"))

            ui.render_spacer()

            try:
                handle_choice(choice)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Something failed unexpectedly: %s", exc)
                logger.error(
                    "Check that the folder is writable and that files are not open or in use."
                )
                ui.pause()

    except KeyboardInterrupt, EOFError:
        ui.render_spacer()
        ui.render_message("Force quitting...", "error")
        sys.exit(0)


if __name__ == "__main__":
    main()
