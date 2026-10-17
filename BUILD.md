# Table of Contents

- [Platforms](#platforms)
- [Getting the Source Code](#getting-the-source-code)
- [Dependencies](#dependencies)
- [Compiling](#compiling)
  - [Windows](#windows-details)
  - [Linux](#linux-and-macos)
  - [macOS](#linux-and-macos)
- [Running the Tests](#running-the-tests)

# Platforms

| Operating System | Supported Versions                                 | Architecture | Tested |
|------------------|----------------------------------------------------|--------------|--------|
| Windows          | 11, 10 (1809 or higher)                            | 64-Bit       |   ✅   |
| GNU/Linux        | Debian 13, Ubuntu 22.04, Fedora 44, Arch Linux     | 64-Bit       |   ✅   |
| macOS            | 14.4 (Ventura) and higher                          | ARM64        |   ❌   |

# Getting the Source Code

- Download the zip archive from the [latest release](https://github.com/Mitra-88/WorkshopDecompressor/releases/latest). `Source code (zip)`

# Dependencies

To compile Workshop Decompressor you will need the following:

- [uv](https://docs.astral.sh/uv/) to manage the Python interpreter and the Python dependencies. Install it with:
```sh
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

The remaining requirements are installed by `uv sync` from `pyproject.toml` and `uv.lock`, so you do not need to install them by hand:

- [Python](https://www.python.org/) 3.15 or later
- [PyInstaller](https://www.pyinstaller.org/) 6.22.3 or later
- [Rich](https://rich.readthedocs.io/en/latest/) 15.0.0 or later

# Compiling

## Windows

In PowerShell:
```sh
cd WorkshopDecompressor
uv python install 3.15
uv sync --frozen
git rev-parse --short HEAD > Src\build_commit.txt
uv run python .github/scripts/freeze_tool_versions.py
```
```sh
uv run pyinstaller --noconfirm --onefile --console --icon "Assets/Icon/WorkshopDecompressor.ico" --name "WorkshopDecompressor" --clean --optimize "2" --version-file "version.txt" --add-data "Src\build_commit.txt;." --add-data "Src\build_tools.txt;." --add-data "Src\Bin\Windows;Bin\Windows"  "Src/Core/cli.py"
```

Without the `git rev-parse` line (for example from a source zip with no git repo) the build still works, the version string just shows `(release)` or `(dev)` instead of the commit. The same goes for the freeze script, which writes `Src/build_tools.txt` with the PyInstaller, Rich and bundled 7-Zip versions the Build Info screen reports. Skip it and the exe still runs, Build Info just shows `PyInstaller bundled, Rich bundled, 7-Zip (bundled)`, because a frozen build carries no package metadata to read those versions from.

## Linux and macOS

In Terminal:
```sh
cd WorkshopDecompressor
uv python install 3.15
uv sync --frozen
git rev-parse --short HEAD > Src/build_commit.txt
uv run python .github/scripts/freeze_tool_versions.py
```
```sh
uv run pyinstaller --noconfirm --onefile --console --strip --name "WorkshopDecompressor" --clean --optimize "2" --add-data "Src/build_commit.txt:." --add-data "Src/build_tools.txt:." --add-data "Src/Bin/Linux:Bin/Linux"  "Src/core/cli.py"
```

On macOS use `Src/Bin/Darwin:Bin/Darwin` as the last `--add-data` instead.

# Running the Tests

The tests need nothing special. uv plus the files already in the repo
(the tools in `Src/Bin` and the samples in `Src/Test`) is all it takes.

From the repo folder, after `uv sync`:

```sh
uv run python -m unittest discover -s Src/Test -v
```

Or on Windows, driving the venv directly:

```sh
.venv\Scripts\python.exe -m unittest discover -s Src\Test -v
```

And on Linux / macOS:

```sh
.venv/bin/python -m unittest discover -s Src/Test -v
```

The tests make sure of things like:

- old `.bin` files work. 7-Zip complains about "data after the end of the
  payload data" on these, that is normal and the tool knows it.
- every archive type (zip, rar, 7z, tar, tar.gz, tar.xz, tar.bz2) really goes
  through 7-Zip and comes out complete, including the ones that need a second
  pass for the tar inside.
- `.gma` files come out with the right content through fastgmad.
- the tool never uses more workers than it should, no matter how many cores
  your machine has.
- the system info line has no weird double spaces.

And then there is the big one: it creates 60 fake addons (400 KB up to 60 MB,
big ones are rare) plus 15 fake `.bin` files, unpacks all of them, and checks
every extracted file is there and the right size. It writes about 1 GB once
in a temp folder and deletes it afterwards, so your SSD is fine.

If you only want those fake files and skip the test part, run this and they
end up in `dist\volume`:

```sh
uv run python Src/Test/test_gma_volume.py --dist
```

On Linux / macOS:

```sh
uv run python3 Src/Test/test_gma_volume.py --dist
```

Handy if you want to try the program on them yourself.
