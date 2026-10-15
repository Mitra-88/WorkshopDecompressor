# Workshop Decompressor


<div align="center">
  <img src="Assets/Icon/WorkshopDecompressor-README.png" alt="Yeah" width="256" height="256">
</div>

**Workshop Decompressor** is a command-line tool for players of Garry's Mod who need to extract content from addon files. This utility supports both modern `.gma` addons and legacy `.bin` addons, a tool for players who download addons from sources such as SteamCMD, third-party programs, websites, or for those using offline versions of the game.

## Key Features

- Cross-Platform: Works on Windows, macOS, and Linux.
- Addon Extraction: Extract both modern `.gma` and legacy `.bin` addon formats.
- Archive Extraction: Unpacks `.zip`, `.rar`, `.7z`, `.tar`, `.tar.gz`, `.tar.xz` and `.tar.bz2` files with the included 7-Zip, so there is nothing to install.
- Multithreading: Utilizes concurrent processing that adapts to your CPU, leaving headroom so your desktop stays responsive.
- Easy to Use: A simple command-line interface.
- Drop-in replacement for GWTool.

## Coming from GWTool?

Both tools can extract Garry's Mod addons, but they take different approaches. GWTool is a Windows-only GUI that's been around for years, while Workshop Decompressor is a modern, cross-platform tool that aims to make extracting addons as simple as possible.

| **What people actually care about** | **GWTool**              | **Workshop Decompressor** |
| -----------------------------------|--------------------------|---------------------------|
| Works on Windows                   | ✅                       | ✅                        |
| Works on macOS & Linux             | ❌                       | ✅                        |
| Open modern `.gma` files           | ✅                       | ✅                        |
| Open legacy `.bin` files           | ⚠️ Multiple manual steps | ✅ Just drop it in        |
| Handles ZIP, RAR, 7Z, TAR...       | ❌                       | ✅                        |
| Still getting updates              | ❌ Last updated in 2012  | ✅ Ongoing development    |

## System Requirements

**RAM Usage:** 40MB<br>
**Disk Space:** 50MB

| Operating System | Supported Versions                                       | Architecture | Tested   |
|------------------|----------------------------------------------------------|--------------|----------|
| Windows          | 11, 10 (1809 or later)                                   | 64-Bit       | ✅ Yeah  |
| GNU/Linux        | Debian 13, Ubuntu 26.04, Fedora 44, Arch Linux, OpenSUSE | 64-Bit       | ✅ Yeah  |
| macOS            | 27, 26, 15, 14, 13, 12                                   | ARM64        | Probably works? No Mac to test on, setting up a VM is a nightmare |

## Good to know

- Legacy addons (`.bin`) sometimes make 7-Zip print a scary "data after the end of the payload data" error. The files still extract fine.
- The folder you run it from needs to be writable.
- On Linux and macOS, run `chmod +x WorkshopDecompressor` once, so the program is allowed to start. The bundled tools should fix their own permissions automatically.

## How to use it

1. Download the program from the [latest release page](https://github.com/Mitra-88/WorkshopDecompressor/releases/latest).
2. Put it in the folder with your addons. If you use SteamCMD, that is usually `steamapps/workshop/content/4000`.

<img src="Assets/Screenshot-1.png" alt="Program placed in the SteamCMD addon folder">

3. Run it and pick an option.

<img src="Assets/Screenshot-2.png" alt="Program scanning a folder of addons">


**When it's finished:** everything you unpacked will be in the `Extracted-Addons` folder (or a folder right next to the archive). Your original files are safely kept in `Leftover` think of it as a backup copy. Once you're happy everything worked, feel free to delete `Leftover` to clean up.

## Building Workshop Decompressor from Source

Please refer to the [build instructions](BUILD.md) for details on building Workshop Decompressor from source.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue to discuss changes.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

## Credits

- [PyInstaller](https://www.pyinstaller.org/): For creating standalone executables.
- [FastGMAD](https://github.com/WilliamVenner/fastgmad): Fast reimplementation of gmad (forked).
- [7-zip](https://www.7-zip.org/): For extracting `.bin`, `.rar`, and all other supported archive formats (forked).
- [Rich](https://rich.readthedocs.io/en/latest/) For beautiful console formatting, progress bars, and enhanced terminal output.
