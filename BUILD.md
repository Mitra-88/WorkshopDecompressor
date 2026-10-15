# Table of Contents

- [Platforms](#platforms)
- [Getting the Source Code](#getting-the-source-code)
- [Dependencies](#dependencies)
  - [Windows](#dependencies)
  - [Linux](#linux-dependencies)
  - [macOS](#dependencies)
- [Compiling](#compiling)
  - [Windows](#windows-details)
  - [Linux](#linux-and-macos)
  - [macOS](#linux-and-macos)
- [Running the Tests](#running-the-tests)

# Platforms

| Operating System | Supported Versions                                       | Architecture | Tested   |
|------------------|----------------------------------------------------------|--------------|----------|
| Windows          | 11, 10 (1809 or later)                                   | 64-Bit       | ✅ Yeah  |
| GNU/Linux        | Debian 13, Ubuntu 26.04, Fedora 44, Arch Linux, OpenSUSE | 64-Bit       | ✅ Yeah  |
| macOS            | 27, 26, 15, 14, 13, 12                                   | ARM64        | Probably works? No Mac to test on, setting up a VM is a nightmare |

# Getting the Source Code

- Download the zip archive from the [latest release](https://github.com/Mitra-88/WorkshopDecompressor/releases/latest). `Source code (zip)`

# Dependencies

You need the following to compile Workshop Decompressor:

- [Python](https://www.python.org/) 3.12+ (latest version is preferred)
- [PyInstaller](https://www.pyinstaller.org/) 6.22.3+

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
.venv\Scripts\activate.bat
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --console --icon "Assets/Icon/WorkshopDecompressor.ico" --name "WorkshopDecompressor" --clean --optimize "2" --version-file "version.txt"  "Src/Core/cli.py"
Copy-Item -Path "Src/Bin" -Destination "dist" -Recurse -Force
```

## Linux and macOS

In Terminal:
```sh
cd WorkshopDecompressor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --console --name "WorkshopDecompressor" --strip --clean --optimize "2" "Src/core/cli.py"
cp -r Src/Bin dist/
```

# Running the Tests

The tests need nothing special. Python plus the files already in the repo
(the tools in `Src/Bin` and the samples in `Src/Test`) is all it takes.

From the repo folder, with the venv active:

```sh
python -m unittest discover -s Src/Test -v
```

Or on Windows, without activating anything:

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
python Src/Test/test_gma_volume.py --dist
```

On Linux / macOS:

```sh
python3 Src/Test/test_gma_volume.py --dist
```

Handy if you want to try the program on them yourself.
