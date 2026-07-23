import sys
import platform

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from extract_addons import main as extract_addons
from extract_archives import main as extract_archives
from utils import get_system_info, app_version, build_date
from py7zr import __version__ as py7zr_version
from rarfile import __version__ as rarfile_version
from PyInstaller import __version__ as pyinstaller_version

console = Console()


def set_cli_title():
    title = f"Workshop Decompressor {app_version}"
    system = platform.system()

    if system == "Windows":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()


def display_info():
    console.print(Panel.fit(
        f"[bold cyan]Workshop Decompressor[/] [dim]{app_version}[/]",
        border_style="cyan"
    ))


def display_build_info():
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="white")

    table.add_row("Program", f"Workshop Decompressor {app_version}")
    table.add_row("Build Date", build_date)
    table.add_row("Operating System", get_system_info())
    table.add_row("Dependencies", f"PyInstaller {pyinstaller_version}, Py7zr {py7zr_version}, RarFile {rarfile_version}, Rich 15.0.0, 7-Zip 26.02")

    console.print(Panel(
        table,
        title="[bold cyan]BUILD INFORMATION[/]",
        border_style="cyan",
        expand=False
    ))


def display_menu():
    menu_text = (
        "[1] [bold]Extract Addons[/]      [dim]Extract GMA and BIN addon files[/]\n"
        "[2] [bold]Extract Archives[/]    [dim]Extract ZIP, RAR, 7Z, TAR files[/]\n"
        "[3] [bold]Help[/]                [dim]Show help menu[/]\n"
        "[4] [bold]Build Info[/]          [dim]Show system and build info[/]\n"
        "[5] [bold]Exit[/]                [dim]Close program[/]"
    )
    console.print(Panel(
        menu_text,
        title="[bold cyan]MAIN MENU[/]",
        border_style="cyan",
        expand=False
    ))


def display_help():
    help_text = (
        "[1] Extract Addons   - Extract GMA and BIN addon files\n"
        "[2] Extract Archives - Extract ZIP, RAR, 7Z, TAR files\n"
        "[3] Help             - Show this menu\n"
        "[4] Build Info       - Show system + build info\n"
        "[5] Exit             - Close program"
    )
    console.print(Panel(
        help_text,
        title="[bold cyan]HELP MENU[/]",
        border_style="cyan",
        expand=False
    ))


def pause():
    console.input("\n[dim]Press ENTER to return to menu...[/]")


def handle_choice(choice):
    match choice:
        case "1":
            extract_addons()
        case "2":
            extract_archives()
        case "3":
            display_help()
        case "4":
            display_build_info()
        case "5":
            console.print("\n[bold green]Exiting... Goodbye![/]\n")
            sys.exit(0)

    pause()


def main():
    set_cli_title()
    try:
        display_info()
        while True:
            console.print()
            display_menu()
            
            choice = Prompt.ask(
                "[bold yellow]Select an option[/]",
                choices=["1", "2", "3", "4", "5"],
                show_choices=False
            )
            console.print()
            handle_choice(choice)
            
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]Force quitting...[/]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
