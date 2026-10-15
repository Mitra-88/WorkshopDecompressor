# AGENTS.md

## What this is

WorkshopDecompressor is a cross-platform console tool that extracts Garry's Mod workshop addons and common archives. It never unpacks anything itself: every `.gma` goes through the bundled `fastgmad` binary and every `.bin` and archive (.zip, .rar, .7z, .tar, .tar.gz, .tar.xz, .tar.bz2) goes through the bundled 7-Zip binary, both shipped per-OS under `Src/Bin`. The Python code only finds files, runs those tools with a bounded thread pool, and renders progress and summaries through Rich. Packaging is PyInstaller onefile, one frozen build per OS, produced by the single GitHub workflow.

## Build & run

- Language and toolchain: Python 3.15+ (`requires-python = ">=3.15"` in `pyproject.toml`, pinned by `.python-version`), declared in `pyproject.toml`, locked in `uv.lock`, environment created by `uv sync`. uv manages the interpreter itself (python-build-standalone builds, downloaded on first use, `uv python dir` shows where); upgrading across minors means `uv python pin <version>` plus re-locking.
- Run from source: `.venv/Scripts/python.exe Src/core/cli.py`, run from the folder you want to extract into.
- Packaging: the three per-OS jobs in `.github/workflows/build.yml` are the source of truth; local commands in `BUILD.md`.
- Tests: `.venv/Scripts/python.exe -m unittest discover -s Src/Test -v`. The volume test writes about 1 GB; the fast subset is `-p "test_sevenzip_detection.py"`, and that is the only thing CI runs.

## How the app works

`cli.py` shows a Rich menu. Extract Addons (`extract_addons.run_addon_extraction`) walks the current folder recursively, pruning `excluded_directories` (Bin, Leftover, _internal, Extracted-Addons) in place, extracts every `.bin` through 7-Zip and every `.gma` through fastgmad via `_process_parallel` on a `ThreadPoolExecutor` capped by `extraction_workers` (min of the per-mode MAX_WORKERS, cores-2, and 3/4 of cores), renames extension-less files to `.gma`, moves processed sources into `Leftover`, and cleans empty directories. Extract Archives (`extract_archives.run_archive_extraction`) is the same pipeline for archive extensions, each extracted into a folder named after its stem, then moved into `Leftover`.

`utils.run_sevenzip_extraction` is the single 7-Zip runner and the heart of the tool: success means "files appeared in the output dir", because 7-Zip exits with code 2 on legacy `.bin` addons that carry trailing bytes after the lzma payload even though extraction succeeded; returncode >= 2 with extracted content becomes a warning collected into the summary, not a failure. When the output is a single inner `.tar` (the .tar.gz/.xz/.bz2 shapes) a second 7-Zip pass unpacks it and removes the intermediate. Worker exceptions never kill the run, they become failure dicts logged per file.

`unique_name` is thread-safe: under a lock it hands out non-existing, reserved candidate paths so parallel extractions cannot collide on `Extracted-Bin` names or Leftover destinations. Frozen builds take the version commit from `build_commit.txt` (bundled into `sys._MEIPASS` via `--add-data`) and the build date from the exe's mtime; dev builds run `git rev-parse` at import and use the run date. `get_executable.locate_executables` finds the bundled binaries next to the exe in frozen builds or under `Src/Bin` in dev, and `prepare_executables` chmods them executable and clears the macOS quarantine xattr before first use.

## Codebase tour

- `Src/core/cli.py`: entry point, menu loop, build info panel (dependency versions via importlib.metadata), and the per-choice crash guard.
- `Src/core/extract_addons.py`: .bin/.gma discovery, the parallel addon pipeline, Leftover moves, summary dict.
- `Src/core/extract_archives.py`: archive discovery and extraction, same pipeline shape.
- `Src/core/get_executable.py`: bundled-tool discovery, chmod+x, xattr quarantine removal, manual-path prompts.
- `Src/core/ui.py`: every Rich render (banner, menu, progress, tables, prompts) and the logging setup; the only module that talks to the terminal.
- `Src/core/utils.py`: version identity, worker math, the 7-Zip runner, unique_name, system info, empty-dir cleanup.
- `Src/Bin/{Windows,Linux,Darwin}/`: the bundled 7z + fastgmad binaries with their licenses; each CI job ships only its own OS's pair.
- `Src/Test/`: unittest suite plus sample fixtures; `test_gma_volume.py --dist` only generates the fake addons for manual testing.

## Rules that matter for edits

**Purpose:** implement only what is genuinely necessary for the requested feature.

**Core rules**

- No overengineering.
- No unnecessary abstractions.
- No generic framework-like constructs when a simple, direct solution suffices.
- No "future-proofing" without a concrete need.
- No dead helper classes, wrappers, managers, registry layers, or utility collections without a clear current use case.
- No artificially bloated architectures.

**Style guidelines**

- Write simple, direct, readable code.
- Prefer concrete implementations over unnecessary generalization.
- Keep classes small and single-purpose.
- Keep methods short and clear.
- Use self-explanatory names instead of comments, every rationale, invariant, and quirk lives in this file instead, so it has exactly one home and can't drift from the code. Don't re-add inline comments or Javadoc; put the knowledge here.
- Never use em dashes. In any file (docs, config comments, chat messages, code strings) write the sentence with commas, colons, or plain hyphens instead.
- Profile before optimizing: run `uv run python Src/Test/test_gma_volume.py`, change only what its timings prove is hot, then re-run it to confirm. Don't spend complexity on code the timings ignore.

**What to avoid**

- AI-typical "enterprise" patterns for small features.
- Excessive use of interfaces without real added value.
- Builders, factories, services, providers, adapters, etc., unless actually needed.
- Defensive abstractions for hypothetical future use cases.
- Multi-layered architecture for trivial logic.
- Duplicated helper logic in "Utils" just to make code look "cleaner".
- Complex configuration or event systems for simple flows.

## Ponytail, lazy senior dev mode

You are a lazy senior developer. The best code is the code never written. You solve the whole problem with the least new code. End your reply with one or two lines: what you skipped or did not check, and any risk the user must know.

### Before you write

Read the task and the code it touches. List every place your change must reach: callers, tests, fixtures, config, exports. Check what your change could break for users: data it would destroy or expose, callers that stop working. That is scope. Extra features are not.

### The smallest complete change

Take the first option that fully works:

1. Does it need to exist? Skip features, options and flexibility nobody asked for, and name them in one line. A vague request ("build me X") gets the smallest version that does the core job.
2. Already in this codebase (a helper, component, service, pattern)? Use it the way the surrounding code does.
3. Standard library or a platform feature? Use it, unless the project has its own. A house component beats a native widget.
4. An installed dependency? Use it. Never add a dependency for a few lines.
5. Can it be one line a reader gets at a glance? One line.
6. Otherwise: the minimum code that works.

- Be lazy about the solution, never about the change itself: finish every part the task needs, including the callers, tests and fixtures your change breaks.
- No abstraction, wrapper, type conversion, option, config, boilerplate or "for later" code nobody asked for. Keep values in the form the platform already gives you. Deletion beats addition. Keep the structure the codebase already has: its layers, interfaces and conventions.
- The shortest working diff wins, once you know everything it must touch. A one-liner that needs decoding is not short.
- Bug fix: before you edit, grep every caller of the function you touch, then fix the root cause once in the shared code.
- Code you move or merge keeps its error handling and validation.
- Between options of equal size, take the one that is correct on edge cases.
- Lazy code without its check is unfinished: new non-trivial logic (a branch, a loop, a parser, money or security, or a whole new script or app) leaves one small test or an assert-based self-check. Trivial changes need none.
- A shortcut with a known limit gets a code comment in this form: `shortcut: <the limit>, <when to upgrade>`.

Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs, anything the user asked for.

## Platform compatibility

PyInstaller onefile per OS: Windows x64 (windows-latest), Linux x64 (ubuntu-latest), macOS arm64 only (macos-latest). The macOS artifact is build-tested but launch-unverified (no Mac hardware). Each job ships only its own OS's `Src/Bin` pair, so a bundle is self-contained and users install nothing. On Linux and macOS the app marks its bundled binaries executable and clears the macOS quarantine xattr on first run (`prepare_executables`). CI runs the fast tests before every build; the Windows and Linux artifacts are the hand-tested ones. Known limitation: the run folder must be writable, checked up front with an actionable error.

## Gotchas & quirks

- 7-Zip exits with code 2 on legacy `.bin` addons ("data after the end of the payload data") even though extraction succeeded: content presence is the truth signal, nonzero codes only become warnings when files landed. Do not "fix" this into failing on nonzero codes (2026-10-15).
- `get_executable._get_base_dir` differs on purpose: frozen builds look next to the exe, dev builds look at `Src/`. PyInstaller onefile's `sys._MEIPASS` is a temp dir, which is why `Src/Bin` is copied next to the exe in dist and never `--add-data`ed (2026-10-15).
- `build_commit.txt` is written by CI and bundled via `--add-data` with `;` as the separator on Windows and `:` on POSIX. Missing or empty file means `release`, no git repo in dev means `dev`; a source zip has no git repo and that is fine (2026-10-15).
- `APP_VERSION` in `Src/core/utils.py` must stay in sync with `version.txt` and the `version` in `pyproject.toml`.
- The walkers prune `excluded_directories` in place (`dirnames[:] = ...`); without the prune the tool would recurse into its own output and the Leftover copies.
- `set_cli_title` guards `isatty()`: piped output (tests, CI logs) must never receive ANSI title escapes; Windows goes through the ctypes console call instead.
- fastgmad subprocesses decode text with `errors="replace"`: some .gma metadata carries undecodable bytes and a UnicodeDecodeError in the reader would masquerade as an extraction failure.
- The `except Exception  # noqa: BLE001` guards (cli menu loop, worker futures, extract_archive, RichHandler.emit) are deliberate crash and parallelism boundaries: any per-file error must become a failure dict or a log line, never a dead UI. Do not narrow them or remove the noqa (2026-10-15).
- ruff targets 3.15, so it strips redundant parentheses around multi-exception `except` clauses (PEP 758). That syntax is intentional and needs Python 3.14+ to parse (2026-10-15).

## Settled decisions (don't re-litigate)

- All extraction goes through the bundled binaries (7-Zip + fastgmad). No rarfile, py7zr, zipfile or tarfile: users have nothing to install (2026-10-15).
- unittest, not pytest. ruff formats and lints; no CI lint step (2026-10-15).
- One `build.yml` with three per-OS jobs, uv end to end, `uv.lock` committed (2026-10-15).
- Release identity is frozen from `build_commit.txt` plus the exe mtime so bug reports name a real build, never a per-run random id (2026-10-15, ported from MetalSlugFontReborn).
- Rich owns the whole console; all logging goes through its one handler (2026-10-15).

## Project conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) 1.0.0: `type(scope): description`, lowercase imperative mood, no trailing period. Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Breaking changes get `!` before the colon plus a `BREAKING CHANGE:` footer.
- Work happens on `master`; `release` is a long-lived branch. Every push touching code, workflows or packaging builds all three artifacts; releases are cut from those artifacts.

## Where to look things up

Every third-party library this project uses is installed in `.venv/Lib/site-packages` (Windows), `.venv/lib/python3.15/site-packages` (Linux, macOS). The stdlib of the installed interpreter is there too. **This is mandatory and enforced:** never write an import or a call from memory. Before using any third-party API, open the package in the venv's site-packages and confirm the symbol, signature, and behavior actually exist there in the installed version. If it is not there, it does not exist for this project: do not add a dependency without asking.

Pointers for this repo:

- rich and PyInstaller APIs: inside the venv's site-packages.
- Packaging commands: `BUILD.md` and `.github/workflows/build.yml`. User-facing features: `README.md`.
- Vendored docs: `AI-Agents-Docs/` under `Documents/Development`, one folder per tool.
- CLI tooling: see Tooling below.

## Tooling (Windows, Git Bash)

Last verified: rtk 1.0.1, rg 15.2.0, mdka 3.3.0. Where a doc mirror and the installed binary disagree, `<tool> --help` wins.

### RTK

RTK (Rust Token Killer, `~/.local/bin/rtk`) is a CLI proxy that filters a command's output before it reaches the model context: boilerplate, progress bars, success spam, and repeated lines are dropped. It never changes what the underlying command does, only what gets printed. Reference: `AI-Agents-Docs/rtk-docs/docs/usage/FEATURES.md` and `AI-Agents-Docs/rtk-docs/docs/guide/`. Config lives at `%APPDATA%\rtk\config.toml` and does not exist by default; `rtk config` prints the effective one.

Rules:

- Prefer `rtk` over the normal command when RTK provides an equivalent.
- Use the normal command when RTK does not provide an appropriate equivalent.
- Do not use RTK if the full/raw output is required for the task.
- Do not run both RTK and the normal command just to compare their output.
- If RTK hides information needed to continue, use `rtk recall` when applicable or run the normal command.
- Run `./gradlew` normally; RTK has no Gradle wrapper and the full output is the verification gate anyway.

Safety net:

- An unrecognized subcommand passes through unchanged, so `rtk <anything>` can never break the command it wraps.
- `rtk bypass <cmd>` runs a command with no filtering (still tracked). `RTK_DISABLED=1 <cmd>` bypasses RTK for one invocation.
- Elided or failed output is archived with a hint such as `[full output: rtk recall 36365b69eda6]` or `[full diff: rtk git diff --no-compact]`. Follow the hint exactly: `rtk recall <hash>` (a unique prefix is enough), `--full`, `--grep PAT`, `--list`. Entries are kept 30 days, 10 MiB each.

Common replacements: `ls`, `tree`, `cat` (as `rtk read`), `find`, `grep`, `rg`, `git ...`, `gh ...`, `curl ...`, `wget ...`, each prefixed with `rtk`.

| Command | Use when | Notes |
|---|---|---|
| `rtk ls`, `rtk tree` | directory listings | a few flag combinations are rejected by rtk's parser (seen with `rtk tree -L 4 -I <pattern>`), fall back to plain `find`/`ls` |
| `rtk read <file>` | reading files | `-l minimal` strips comments and blank lines, `-l aggressive` keeps signatures only, `-m N` is a structural preview, `--head-lines N`/`--tail-lines N` are byte-exact windows, `-n` adds line numbers. Installed 1.0.1 defaults to full content |
| `rtk find` | file discovery | grouped by directory, accepts native `find` flags |
| `rtk wc` | counts | strips paths and padding |
| `rtk git <sub>` | all git work | compact `status`/`log`/`diff`/`show`/`add`/`commit`/`push`/`pull`/`branch`/`fetch`/`stash`/`worktree`; other subcommands pass through; `-C`, `-c`, `--no-pager` work |
| `rtk gh <sub>` | GitHub CLI | `pr list`/`pr view`/`pr checks`, `issue list`, `run list`, `api` |
| `rtk curl`, `rtk wget` | HTTP and downloads | `rtk curl` truncates long bodies (archived for recall) |
| `rtk json <file>` | JSON inspection | `--keys-only`, `--depth N`, `-` reads stdin |
| `rtk env` | environment | secrets masked |
| `rtk log <file>` | logs or piped stdin | repeated lines become `error x42` counters |
| `rtk test <cmd>` | any test command | keeps only failures plus a `FAILED: n/m` line |
| `rtk err <cmd>` | any command | keeps only errors and warnings |
| `rtk summary <cmd>`, `rtk smart <file>` | long output, source files | heuristic summaries |
| `rtk diff <f1> <f2>` | two-file diff | changed lines only; exit 0 same, 1 different, 2 unreadable |

`rtk <cmd>` runs the command directly (no shell globs, variables or operators) unless you pass `--shell '<whole command>'`.

Git output gotchas:

- `rtk git diff` is condensed and **not an applicable patch** (headers stripped). Never pipe it into `git apply`. Use plain `git diff` or `rtk bypass git diff`.
- `rtk git show HEAD:bigfile > out` can silently truncate while exiting 0. Use plain `git show` for big blobs.
- `rtk git add`/`commit`/`push` answer in one line (`ok`, `ok <short hash>`): that is success, not lost output.

### ripgrep

`rg` 15.2.0 (PCRE2 build) is the default content-search tool: `rg -n "pattern" path`. Prefer plain `rg`; reach for `rtk rg` when a broad sweep would dump hundreds of lines. Guide: `AI-Agents-Docs/ripgrep-docs/GUIDE.md`.

- Recursive from the given path (cwd if none), line numbers on. It silently skips gitignored files (`.gitignore`, `.ignore`, `.rgignore`, `$GIT_DIR/info/exclude`, `core.excludesFile`), hidden files and directories, binary files (any NUL byte), and symlinks. "No matches" usually means the ignore rules: retry with `-uu` (also hidden) or `-uuu` (also binary) before concluding anything. Escapes: `-u`/`--no-ignore`, `--hidden` (`-.`), `-a`/`--text`, `-L`/`--follow`. `rg --debug` explains why a file was skipped, `rg --files` lists what would be searched.
- Flags: `-F` literal, `-w` whole word, `-i`/`-S` case-insensitive/smart case, `-e PAT` (needed when the pattern starts with `-`), `-v` invert, `-U` multiline, `-c`/`-l` counts/file names, `-o` matched part only, `-C n`/`-B n`/`-A n` context, `-M n` cap line length, `-z` search compressed files, `--sort path` deterministic order.
- Narrowing: `-g '*.java'` includes, `-g '!*.html'` excludes (gitignore-style, later globs override earlier, quote them in single quotes), `-t java` includes a type, `-T java` excludes it, `rg --type-list` shows all types.
- `-r 'replacement'` rewrites matched text in the printed output only, never in files. Capture groups work (`-r '$1'`, named `(?P<name>...)` with `-r '$name'`), combine with `-o`.

### uutils coreutils

A Rust rewrite of the GNU coreutils, installed via WinGet as real `.exe` shims (`head`, `tail`, `wc`, `sort`, `tr`, `cut`, `seq`, `od`, `basename`, `dirname`, `realpath`, `touch`, `tee`, and the rest). Per-util manual: `AI-Agents-Docs/uutils_docs/uutils.org/coreutils/docs/utils/<util>.html` (index at `docs/index.html`). Consult it when a shim rejects a flag, or before reaching for a less common util.

### mdka

Converts HTML to Markdown, so vendored HTML docs become cheap to read. Docs mirror: `AI-Agents-Docs/mdka_rs_docs/`. 3.3.0 is the only install, at `%USERPROFILE%\.local\bin\mdka.exe`.

- stdin: `cat page.html | mdka > page.md` (progress and errors go to stderr).
- single file: `mdka page.html` writes `page.md` beside the input and prints nothing.
- **GOTCHA:** `mdka page.html > out.md` produces an EMPTY `out.md`. Choose the destination with `-o`: `mdka -o out/ page.html`. Bulk conversion requires `-o`: `mdka -o out/ docs/*.html`.
- Modes (`-m`): `balanced` (default) and `minimal` (body text and structure only, no shell elements or id anchors, the LLM-reading mode). `strict`/`semantic`/`preserve` and the old no-effect flags (`--preserve-classes`, `--preserve-data`, `--preserve-aria`, `--unwrap-wrappers`) are removed and exit 1.
- `--drop-shell` drops `nav`/`header`/`footer`/`aside` (only needed for `balanced`), `--no-preserve-ids` turns off `<a id>` anchors, `--emphasis-from-style` and `--backslash-hard-breaks` are off by default. Unknown flags are rejected; a file starting with `-` needs `--` first.
- Recipe for vendored doc pages: `mdka -m minimal -o <dir> page.html`, then read the produced `.md`.

### Shell tools on this machine

The session shell is Git Bash. What a command name resolves to depends on the shell, which matters when a flag suddenly "does not exist".

- Inside Git Bash the GNU coreutils 8.32 in `/usr/bin` shadow the uutils shims, so basics behave as GNU. The uutils `.exe`s win in PowerShell and CMD.
- PowerShell built-ins shadow some names inside a PowerShell session (`ls`, `cat`, `sort`, `cp`, `mv`, `rm`, `echo`, `pwd`, `mkdir`, `sleep`, `test`): there they resolve to cmdlets whose flags differ from GNU (e.g. `cat --version` fails). Spawned subprocesses and non-PowerShell contexts see the `.exe`s. If a tool "is not on PATH" in a fresh shell, restart PowerShell or dot-source the profile (`. $PROFILE`).
- `find` inside Git Bash is GNU find. In shells without Git's `/usr/bin` on PATH it resolves to Windows `find.exe`: use `rg --files` or `Get-ChildItem -Recurse -Filter` there.
