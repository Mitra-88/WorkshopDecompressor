# Table of Contents

- [Platforms](#platforms)
- [Getting the Source Code](#getting-the-source-code)
- [Dependencies](#dependencies)
  - [Windows](#dependencies)
  - [Linux](#linux-dependencies)
  - [macOS](#dependencies)
- [Compiling](#compiling)
  - [Windows](#windows-details)
  - [Linux](#linux-details)
  - [macOS](#macos-details)

# Platforms

| Operating System | Supported Versions                                         | Architecture |
|------------------|------------------------------------------------------------|--------------|
| Windows          | 11, 10 (1809 or later)                                     | 64-Bit       |
| GNU/Linux        | Debian 13, Ubuntu 24.04.3, Fedora 43, Arch Linux, OpenSUSE | 64-Bit       |
| macOS            | 15, 14, 13, 12                                             | ARM64        |

# Getting the Source Code

- Download the zip archive from the [latest release](https://github.com/Mitra-88/Workshop Decompressor/releases/latest). `Source code (zip)`

# Dependencies

You need the following to compile Workshop Decompressor:

- [Python](https://www.python.org/) 3.12+
- [PyInstaller](https://www.pyinstaller.org/) 6.16.0+
- [Py7zr](https://pypi.org/project/py7zr/) 1.0.0+
- [RarFile](https://pypi.org/project/rarfile/) 4.2+

## Linux Dependencies

For Ubuntu/Debian:
```sh
sudo apt install -y python3 python3-pip python3-venv
```
For Fedora:
```sh
sudo dnf install -y python3 python3-pip python3-virtualenv
```
For Arch:
```sh
sudo pacman -Syu --noconfirm python-pip python-virtualenv
```
For OpenSUSE:
```sh
sudo zypper install -y python3 python3-pip python3-virtualenv
```

# Compiling

## Windows

In Command Prompt:
```sh
cd WorkshopDecompressor
py -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --console --icon "Src/Icon/WorkshopDecompressor.ico" --name "Workshop Decompressor" --clean --optimize "2" --version-file "version.txt" --add-data "Src/extract_addons.py;." --add-data "Src/extract_archives.py;." --add-data "Src/utils.py;."  "Src/cli.py"
Copy-Item -Path "Src/Bin" -Destination "dist" -Recurse -Force
```

## Linux/macOS

In Terminal:
```sh
cd WorkshopDecompressor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --console --name "Workshop Decompressor" --strip --clean --optimize "2" --add-data "Src/extract_addons.py:." --add-data "Src/extract_archives.py:." --add-data "Src/utils.py:."  "Src/cli.py"
cp -r Src/Bin dist/
```
