import importlib.metadata
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEVEN_ZIP_NAME = {"Windows": "7zz.exe", "Linux": "7zz", "Darwin": "7zz"}


def seven_zip_banner():
    system = platform.system()
    binary = ROOT / "Src" / "Bin" / system / SEVEN_ZIP_NAME[system]
    result = subprocess.run(
        [str(binary), "--help"], capture_output=True, text=True, check=True
    )
    first_line = next(line for line in result.stdout.splitlines() if line.strip())
    return first_line.split(" : ")[0].strip()


def main():
    versions = (
        f"PyInstaller {importlib.metadata.version('pyinstaller')}",
        f"Rich {importlib.metadata.version('rich')}",
        seven_zip_banner(),
    )
    text = "\n".join(versions) + "\n"
    (ROOT / "Src" / "build_tools.txt").write_text(text, encoding="utf-8", newline="")
    print(text, end="")


if __name__ == "__main__":
    main()
