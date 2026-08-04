import logging
import platform
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                           TimeElapsedColumn)
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "app.title": "cyan",
        "app.border": "cyan",
        "muted": "grey58",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "cyan",
        "prompt": "yellow",
        "table.header": "cyan",
        "table.label": "cyan",
        "table.value": "white",
        "menu.label": "white",
        "ok": "green",
        "missing": "red",
        "progress.bin": "blue",
        "progress.gma": "green",
        "progress.archive": "cyan",
        "log.time": "grey58",
        "log.info": "cyan",
        "log.warning": "yellow",
        "log.error": "red",
        "log.debug": "grey58",
        "log.message": "white",
    }
)

console = Console(theme=THEME)

_PROGRESS_STYLES = {
    "bin": "progress.bin",
    "gma": "progress.gma",
    "archive": "progress.archive",
}

_LOG_STYLES = {
    "DEBUG": "log.debug",
    "INFO": "log.info",
    "WARNING": "log.warning",
    "ERROR": "log.error",
    "CRITICAL": "log.error",
}


class CleanRichHandler(RichHandler):
    def emit(self, record):
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            level_style = _LOG_STYLES.get(record.levelname, "log.message")

            line = Text()
            line.append(f"[{timestamp} ", style="log.time")
            line.append(record.levelname, style=level_style)
            line.append("]: ", style="log.time")
            line.append(record.getMessage(), style="log.message")

            self.console.print(line)
        except Exception:
            self.handleError(record)


def configure_logging():
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(CleanRichHandler(console=console, markup=False, show_path=False))
    root.setLevel(logging.INFO)
    return logging.getLogger("workshop")


def set_cli_title(title):
    system = platform.system()

    if system == "Windows":
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()


def render_spacer():
    console.print()


def render_message(message, style="table.value"):
    console.print(Text(message, style=style))


def render_rule(title):
    console.rule(Text(title, style="info"))


def _panel_title(text, style="app.title"):
    return Text(text, style=style)


def _key_value_table(rows):
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="table.label", no_wrap=True)
    table.add_column(style="table.value")

    for label, value in rows:
        table.add_row(
            Text(label, style="table.label"),
            Text(str(value), style="table.value"),
        )

    return table


def _summary_panel(title, rows, failures):
    table = _key_value_table(rows)

    if failures:
        table.add_row(
            Text("Failures", style="table.label"),
            Text(str(len(failures)), style="error"),
        )

    console.print(
        Panel(
            table,
            title=_panel_title(title, style="success"),
            border_style="success",
            expand=False,
        )
    )


def render_banner(app_version):
    text = Text()
    text.append("Workshop Decompressor ", style="app.title")
    text.append(app_version, style="muted")

    console.print(Panel.fit(text, border_style="app.border"))


def render_build_info(info):
    console.print(
        Panel(
            _key_value_table(info.items()),
            title=_panel_title("BUILD INFORMATION"),
            border_style="app.border",
            expand=False,
        )
    )


def _render_item_panel(items, title):
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="info", no_wrap=True)
    table.add_column(style="menu.label")
    table.add_column(style="muted")

    for choice, label, description in items:
        table.add_row(
            Text(f"[{choice}]", style="info"),
            Text(label, style="menu.label"),
            Text(description, style="muted"),
        )

    console.print(
        Panel(
            table,
            title=_panel_title(title),
            border_style="app.border",
            expand=False,
        )
    )


def render_menu(items):
    _render_item_panel(items, "MAIN MENU")


def render_help(items=None):
    help_text = Text()

    help_text.append("📂 Setup\n", style="info")
    help_text.append(
        "Place this executable in your addon folder (e.g., steamapps/workshop/content/4000).\n"
    )
    help_text.append(
        "It automatically scans the current directory and all subdirectories.\n\n"
    )

    help_text.append("🔧 Extraction Modes\n", style="info")
    help_text.append("[1] Extract Addons: ", style="menu.label")
    help_text.append("Processes .gma and .bin files. Outputs to 'Extracted-Addons'.\n")
    help_text.append("[2] Extract Archives: ", style="menu.label")
    help_text.append(
        "Unpacks .zip, .rar, .7z, and .tar files. Originals are moved to 'Leftover'.\n\n"
    )

    help_text.append("💡 Tips\n", style="info")
    help_text.append("• Close tools using these files before extracting.\n")
    help_text.append(
        "• If 7-Zip or fastgmad are missing, the tool will prompt for their paths.\n"
    )
    help_text.append(
        "• Empty directories are cleaned up automatically after extraction."
    )

    console.print(
        Panel(
            help_text,
            title=_panel_title("HELP GUIDE"),
            border_style="app.border",
            expand=False,
        )
    )


def prompt_choice(choices):
    return Prompt.ask(
        Text("Select an option", style="prompt"),
        choices=list(choices),
        show_choices=False,
    )


def pause():
    console.print(Text("Press ENTER to return to menu...", style="muted"))
    input()


def confirm_continue(
    title,
    lines,
    cancel_message="Operation cancelled.",
    invalid_message="Invalid input. Please enter 'y' or 'n'.",
):
    text = Text()
    text.append(title, style="warning")
    text.append("\n")
    text.append("────────────────────────\n", style="muted")

    for line in lines:
        text.append(line + "\n")

    text.append("────────────────────────", style="muted")

    console.print(Panel(text, border_style="warning", expand=False))

    while True:
        response = Prompt.ask(Text("Continue? (y/n)", style="prompt")).lower().strip()

        if response in ("y", "yes"):
            return True

        if response in ("n", "no"):
            render_message(cancel_message, "muted")
            return False

        render_message(invalid_message, "warning")


def render_tool_status(rows):
    table = Table(show_header=True, header_style="table.header", show_lines=False)
    table.add_column("Tool", style="table.label", width=12)
    table.add_column("Status", width=12)
    table.add_column("Expected Location", style="table.value")

    for row in rows:
        status = (
            Text("✓ Found", style="ok")
            if row.get("found")
            else Text("✗ Missing", style="missing")
        )

        table.add_row(
            Text(str(row.get("name")), style="table.label"),
            status,
            Text(str(row.get("path")), style="table.value"),
        )

    console.print(table)


def render_missing_tools_panel(missing):
    text = Text()
    text.append("The following tools were not found: ", style="warning")
    text.append(", ".join(missing), style="error")
    text.append("\n\nYou can either:\n")
    text.append("1. Put the missing files into the expected folder shown above, OR\n")
    text.append("2. Provide their absolute paths manually in the next step.\n")
    text.append(
        "Tip: You can drag and drop the file directly into this window.",
        style="muted",
    )

    console.print(
        Panel(
            text,
            title=_panel_title("Tools Missing", style="error"),
            border_style="error",
            expand=False,
        )
    )


def render_directory_status(bin_dir):
    display = str(bin_dir).replace("\\", "/")

    if not bin_dir.exists():
        render_message(f"The expected folder '{display}/' does not exist.", "muted")
        return

    if not bin_dir.is_dir():
        render_message(f"'{display}' exists but is not a folder.", "muted")
        return

    try:
        files = sorted(entry.name for entry in bin_dir.iterdir() if entry.is_file())
    except PermissionError:
        render_message(f"Could not read '{display}/' (permission denied).", "muted")
        return

    if files:
        render_message(f"Files currently in '{display}/': {', '.join(files)}", "muted")
    else:
        render_message(f"The folder '{display}/' is currently empty.", "muted")


def _invalid_path_message(clean_path):
    if not clean_path:
        return "Path cannot be empty."

    path_obj = Path(clean_path)

    if not path_obj.exists():
        return f"Nothing exists at '{clean_path}'. Check for typos and try again."

    if path_obj.is_dir():
        return "That path is a folder, not a file. Point to the executable file."

    if not path_obj.is_file():
        return "That path is not a valid file. Please try again."

    return None


def prompt_absolute_paths(missing_names):
    while True:
        answers = {}

        for name in missing_names:
            while True:
                console.print(Text(name, style="info"))

                raw_path = Prompt.ask(Text("Enter absolute path", style="prompt"))
                clean_path = raw_path.strip().strip('"').strip("'")
                error = _invalid_path_message(clean_path)

                if error:
                    render_message(error, "error")
                    continue

                answers[name] = clean_path
                render_message("File verified.", "success")
                break

        console.print(Text("Please confirm the provided paths:", style="info"))

        for name, path in answers.items():
            line = Text()
            line.append(f"  {name:10s} -> ", style="table.label")
            line.append(path, style="table.value")
            console.print(line)

        response = Prompt.ask(
            Text("Are these correct? (y/n)", style="prompt"),
            choices=["y", "n"],
            default="y",
        ).lower()

        if response == "y":
            render_message("Paths accepted!", "success")
            return answers

        render_message("Let's try again.", "warning")


@contextmanager
def stage_progress(stage, description, total):
    style = _PROGRESS_STYLES.get(stage, "info")

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}", style=style),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(description, total=total)
        yield lambda: progress.advance(task_id)


def render_addon_summary(summary):
    if not summary.get("bin_found", 0) and not summary.get("gma_found", 0):
        console.print(
            Panel(
                Text("No .bin or .gma files found.", style="muted"),
                title=_panel_title("NOTHING TO DO", style="muted"),
                border_style="muted",
                expand=False,
            )
        )
        return

    rows = [
        ("Time", summary.get("elapsed", "")),
        (".bin files", summary.get("bin_processed", 0)),
        (".gma files", summary.get("gma_processed", 0)),
        ("Renamed", summary.get("renamed", 0)),
        ("Output", "Extracted-Addons"),
        ("Moved", summary.get("moved", 0)),
    ]

    _summary_panel("PROCESS COMPLETE", rows, summary.get("failures", []))


def render_archive_summary(summary):
    if not summary.get("found", 0):
        console.print(
            Panel(
                Text("No archives found.", style="muted"),
                title=_panel_title("NOTHING TO DO", style="muted"),
                border_style="muted",
                expand=False,
            )
        )
        return

    rows = [
        ("Time", summary.get("elapsed", "")),
        ("Processed", summary.get("processed", 0)),
        ("Directories cleaned", summary.get("directories_cleaned", 0)),
    ]

    _summary_panel("COMPLETE", rows, summary.get("failures", []))
