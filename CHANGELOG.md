## **Workshop Decompressor v2.9.0 - "One File, No Setup"**
**Release Date:** 2026-10-17

The release that turns Workshop Decompressor into one self-contained executable. It is a large one: 33 commits since 2.8.0. The extraction tools now travel inside the program, the program can repair them if they go missing, and the console reports every step it takes.

### ⚠️ Before You Upgrade
* **CPU requirement:** the bundled 7-Zip and fastgmad builds are compiled for x86-64-v3, so they need AVX2 support: roughly an Intel CPU from 2013 or an AMD CPU from 2015 and newer, with a few entry-level chips from those years falling short. 2.8.0 bundled the official 7-Zip binary, so an older machine may notice this upgrade more than most. There is no older-CPU build of the bundled tools yet, which means supplying your own 7-Zip through the manual-path option.
* **Migration step:** replace the executable and delete any `Bin` folder you keep next to it. A `Bin` folder beside the program takes priority over the tools inside it, so a file left there with a matching name (`7zz`, `7zz.exe`, `fastgmad`, `fastgmad.exe`) is used instead of the bundled copy. The program tests whatever it finds before extracting, so a stale tool that cannot run is reported to you rather than used quietly.
* **Renamed:** the shipped 7-Zip binary is `7zz` on Linux and macOS and `7zz.exe` on Windows, replacing `7z` and `7z.exe`. This only matters if you point the manual-path option at it.
* **Changed behavior:** the version string is now `v2.9.0 (<commit>)` with the build date taken from the file, instead of an identifier regenerated on every start (2.8.0 used a random `uuid4` value). Bug reports now name the exact build. Build Info additionally reports the Python, PyInstaller, Rich and 7-Zip versions, and prints `N/A` for any version it cannot detect.
* **Licenses:** the bundled 7-Zip builds ship with their own `License.txt`, `LICENSE-APACHE` and `LICENSE-MIT` files in `Src/Bin`, next to the binaries they cover.

### 🎵 What's New
* **One file per OS:** Windows, Linux and macOS each get a single executable with 7-Zip and fastgmad inside, and no folder to keep next to it. Each artifact embeds only its own OS's pair of binaries.
* **Tool self-repair:** when a tool is missing or will not run, the program offers to fetch it from the project's nightly releases, verifies the published sha256 or sha512 digest and the byte size while streaming, extracts only the expected executable, and smoke-tests it before use. A failed download rolls back and leaves nothing behind.
* **Update notices:** one background check per launch against the latest GitHub release. A newer version is announced once, with a link, and nothing is ever downloaded. Every failure is silent, and `WORKSHOP_DECOMPRESSOR_NO_UPDATE_CHECK` turns the check off.
* **Console rebuilt:** numbered steps from `[1/6]` to `[6/6]`, live progress with file counts, per-file warnings, and a closing receipt naming the output folder, the elapsed time and the directories cleaned.
* **CPU check:** both tools are run once before an extraction starts. When this CPU cannot execute them, you get the reason and the choice to point the program at your own builds, instead of a folder of failed files with no explanation.
* **Colors:** `NO_COLOR` is honored. Any non-empty value drops ANSI colors and keeps bold and underline styling.

### ⚡ Performance
* **800 MB in 0.68 seconds:** the volume fixture, 60 `.gma` files plus 15 legacy `.bin` files totaling 800 MB, extracted in 0.684 seconds on Windows 11 with 9 workers, using the released Windows executable. These are generated test addons; a real addon folder depends on content and disk speed.
* **Memory stays flat:** peak working set was 38.3 MB during that batch and 37.3 MB during a three-file batch, with the 7-Zip child processes peaking at 9.3 MB. Extraction streams fixed-size chunks to disk from a worker pool sized from the available CPUs (cores minus two, capped at three quarters), so memory does not grow with the number of files.
* **Smaller on disk:** the artifact is 14.04 MB for Windows, 15.27 MB for Linux and 14.38 MB for macOS, against the 25 MB footprint 2.8.0 listed.

### 🛠️ Fixes & Tweaks
* **Legacy `.bin` files:** 7-Zip exits with code 2 on these ("data after the end of the payload data") even though the files extract. This is now reported per file and counted in the summary as a warning, and so is exit code 1, which previously passed silently.
* **Tool recovery:** five failure paths found in review and closed. A missing download folder, an HTML response from a captive portal, a connection dropped mid-transfer, a blocked final move, and an unrecognized platform each ended in a crash or a misleading network message before.
* **`.bin`-only folders:** a folder with no `.gma` files no longer crashes the run.
* **Worker count:** the pool is sized from the CPUs this process may use rather than the total the machine reports, which matters under restricted CPU affinity.
* **Compatibility:** menu options and the `Extracted-Addons` and `Leftover` folders work as in 2.8.0, so existing habits and shortcuts still apply.

### 📚 Docs
* **README:** requirements including the CPU requirement, a measured resource footprint, and steps that match the one-file build.
* **BUILD.md:** per-OS build commands with the tool-version freeze step and the uv setup.
* **AGENTS.md:** new. It holds the project's rationale, quirks and settled decisions in one place.
* **Repository:** work happens on `master` only. The long-lived release branch was removed.

**Full Changelog**: [bc20d84...973f1d9](https://github.com/Mitra-88/WorkshopDecompressor/compare/bc20d84256edb34a94dfd8df6712b0698c6748e4...973f1d9)
