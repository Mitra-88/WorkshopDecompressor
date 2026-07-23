import platform
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

def show_dir_status(bin_dir: Path):
    display = str(bin_dir).replace("\\", "/")

    if not bin_dir.exists():
        console.print(f"[dim]The expected folder '{display}/' does not exist.[/]")
        return

    if not bin_dir.is_dir():
        console.print(f"[dim]'{display}' exists but is not a folder.[/]")
        return

    try:
        files = sorted(e.name for e in bin_dir.iterdir() if e.is_file())
    except PermissionError:
        console.print(f"[dim]Could not read '{display}/' (permission denied).[/]")
        return

    if not files:
        console.print(f"[dim]The folder '{display}/' is currently empty.[/]")
        return

    console.print(f"[dim]Files currently in '{display}/': {', '.join(files)}[/]")

def ask_for_absolute_paths(missing_names):

    while True:
        answers = {}

        for name in missing_names:
            while True:
                console.print(f"\n[bold cyan]{name}[/]")
                raw_path = Prompt.ask("Enter absolute path")
                clean_path = raw_path.strip().strip('"').strip("'")

                if not clean_path:
                    console.print("[red]Path cannot be empty.[/]")
                    continue

                path_obj = Path(clean_path)

                if not path_obj.exists():
                    console.print(f"[red]Nothing exists at '{clean_path}'. Check for typos and try again.[/]")
                    continue
                elif path_obj.is_dir():
                    console.print(f"[red]That path is a folder, not a file. Please point to the actual executable.[/]")
                    continue
                elif not path_obj.is_file():
                    console.print(f"[red]That path is not a valid file. Please try again.[/]")
                    continue

                answers[name] = clean_path
                console.print("[green]File verified.[/]")
                break

        console.print("\n[bold]Please confirm the provided paths:[/]")
        for name, path in answers.items():
            console.print(f"  [cyan]{name:10s}[/] -> {path}")

        if Confirm.ask("Are these correct?", default=True):
            console.print("\n[bold green]Paths accepted![/]\n")
            return answers
        else:
            console.print("\n[yellow]Let's try again.[/]\n")

def get_executable_paths():
    system = platform.system()
    bin_dir = Path("Bin") / system

    executables = {
        "7z":       "7z.exe"       if system == "Windows" else "7z",
        "fastgmad": "fastgmad.exe" if system == "Windows" else "fastgmad",
    }

    console.rule("[bold blue]Tool Setup")

    table = Table(show_header=True, header_style="bold magenta", show_lines=False)
    table.add_column("Tool", style="bold", width=12)
    table.add_column("Status", width=12)
    table.add_column("Expected Location")

    found = {}
    missing = []

    for name, filename in executables.items():
        full_path = bin_dir / filename
        display_path = str(full_path).replace("\\", "/")

        if full_path.exists():
            table.add_row(name, "[green]✓ Found[/]", display_path)
            found[name] = str(full_path)
        else:
            table.add_row(name, "[red]✗ Missing[/]", display_path)
            missing.append(name)

    console.print(table)

    if not missing:
        console.print("\n[bold green]✨ Success! All required tools were found automatically.[/]\n")
        return found

    panel_content = (
        f"The following tools were not found: [bold red]{', '.join(missing)}[/]\n\n"
        "You can either:\n"
        "1. Put the missing files into the expected folder shown above, OR\n"
        "2. Provide their absolute paths manually in the next step.\n"
        "[grey](Tip: You can drag and drop the file directly into this window)[/grey]"
    )
    width = console.measure(panel_content).maximum + 4
    console.print(Panel(
        panel_content,
        title="[bold red]Tools Missing[/]",
        border_style="red",
        width=width
    ))

    show_dir_status(bin_dir)
    console.print()

    return ask_for_absolute_paths(missing)
