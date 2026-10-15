## What this is

WorkshopDecompressor is a cross-platform console tool that extracts Garry's Mod workshop addons and common archives. It never unpacks anything itself: every `.gma` goes through the bundled `fastgmad` binary and every `.bin` and archive (.zip, .rar, .7z, .tar, .tar.gz, .tar.xz, .tar.bz2) goes through the bundled 7-Zip binary, both shipped per-OS under `Src/Bin`. The Python code only finds files, runs those tools with a bounded thread pool, and renders progress and summaries through Rich. Packaging is PyInstaller onefile, one frozen build per OS, produced by the single GitHub workflow.

## Build & run

Dependencies: Python 3.15+ (`requires-python = ">=3.15"` in `pyproject.toml`), managed by uv. `uv sync` builds the `.venv` from the pinned `.python-version` (3.15) and installs rich, pyinstaller and the dev group (ruff) from the committed `uv.lock`. There is no requirements.txt anymore. uv manages the interpreter itself (python-build-standalone builds, downloaded on first use, `uv python dir` shows where); upgrading Python across minors means `uv python pin <version>` plus re-locking.

Run from source, from the folder you want to extract into:

```sh
.venv/Scripts/python.exe Src/core/cli.py
```

Tests: `.venv/Scripts/python.exe -m unittest discover -s Src/Test -v` (headless, no network). The full run includes the volume test that writes about 1 GB; the fast subset is `-p "test_sevenzip_detection.py"`, and that is the only thing CI runs.

Packaging: the three per-OS jobs in `.github/workflows/build.yml` are the source of truth. Each installs uv, `uv python install 3.15`, `uv sync --frozen` with the uv cache keyed on `uv.lock`, runs the fast tests, writes `Src/build_commit.txt` from `git rev-parse`, builds the PyInstaller onefile with `--add-data` for that file, copies `Src/Bin` into dist and deletes the other platforms' binaries.

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

## Settled decisions

- All extraction goes through the bundled binaries (7-Zip + fastgmad). No rarfile, py7zr, zipfile or tarfile: users have nothing to install.
- unittest, not pytest. ruff for formatting and lint, no CI lint step.
- One `build.yml` with three per-OS jobs, uv end to end, `uv.lock` committed.
- Release identity is frozen from `build_commit.txt` plus the exe mtime so bug reports name a real build, never a per-run random id.
- Rich owns the whole console; all logging goes through its one handler.

## Where to look things up

Every third-party library this project uses is installed in `.venv\Lib\site-packages`: rich and PyInstaller. The stdlib of the installed interpreter is there too. **This is mandatory and enforced:** never write an import or a call from memory. Before using any third-party API, open the package under `.venv\Lib\site-packages` and confirm the symbol, signature, and behavior actually exist there in the installed version. If it is not in site-packages, it does not exist for this project: do not add a dependency without asking.

## Gotchas & quirks

- 7-Zip exits with code 2 on legacy `.bin` addons ("data after the end of the payload data") even though extraction succeeded: content presence is the truth signal, nonzero codes only become warnings when files landed. Do not "fix" this into failing on nonzero codes.
- `get_executable._get_base_dir` differs on purpose: frozen builds look next to the exe, dev builds look at `Src/`. PyInstaller onefile's `sys._MEIPASS` is a temp dir, which is why `Src/Bin` is copied next to the exe in dist and never `--add-data`ed.
- `build_commit.txt` is written by CI and bundled via `--add-data` with `;` as the separator on Windows and `:` on POSIX. Missing or empty file means `release`, no git repo in dev means `dev`; a source zip has no git repo and that is fine.
- `APP_VERSION` in `Src/core/utils.py` must stay in sync with `version.txt` and the `version` in `pyproject.toml`.
- The walkers prune `excluded_directories` in place (`dirnames[:] = ...`); without the prune the tool would recurse into its own output and the Leftover copies.
- `set_cli_title` guards `isatty()`: piped output (tests, CI logs) must never receive ANSI title escapes; Windows goes through the ctypes console call instead.
- fastgmad subprocesses decode text with `errors="replace"`: some .gma metadata carries undecodable bytes and a UnicodeDecodeError in the reader would masquerade as an extraction failure.
- The `except Exception  # noqa: BLE001` guards (cli menu loop, worker futures, extract_archive, RichHandler.emit) are deliberate crash and parallelism boundaries: any per-file error must become a failure dict or a log line, never a dead UI. Do not narrow them or remove the noqa.
- ruff targets 3.15, so it strips redundant parentheses around multi-exception `except` clauses (PEP 758). That syntax is intentional and needs Python 3.14+ to parse.

## Coding rules (mandatory: apply to every change)

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

**What to avoid**

- AI-typical "enterprise" patterns for small features.
- Excessive use of interfaces without real added value.
- Builders, factories, services, providers, adapters, etc., unless actually needed.
- Defensive abstractions for hypothetical future use cases.
- Multi-layered architecture for trivial logic.
- Duplicated helper logic in "Utils" just to make code look "cleaner".
- Complex configuration or event systems for simple flows.

# Ponytail, lazy senior dev mode

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here, don't re-write it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it: read the task and the code it touches, trace the real flow end to end, then climb.

Bug fix = root cause, not symptom: a report names a symptom. Grep every caller of the function you touch and fix the shared function once, one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken.

Rules:

- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size, lazy means less code, not the flimsier algorithm.
- Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a `ponytail:` comment naming the ceiling and upgrade path.

Not lazy about: understanding the problem (read it fully and trace the real flow before picking a rung, a small diff you don't understand is just laziness dressed up as efficiency), input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs (the platform is never the spec ideal, a clock drifts, a sensor reads off), anything explicitly requested. Lazy code without its check is unfinished: non-trivial logic leaves ONE runnable check behind, the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)

## Project conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) 1.0.0: `type(scope): description`, lowercase imperative mood, no trailing period. Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Breaking changes get `!` before the colon plus a `BREAKING CHANGE:` footer.

## RTK

RTK (Rust Token Killer, `rtk` 1.0.1 at `~/.local/bin/rtk`) is a CLI proxy that filters a command's output before it reaches the model context: boilerplate, progress bars, success spam, and repeated lines are dropped, what matters stays. It never changes what the underlying command does, only what gets printed. Full reference: `AI-Agents-Docs/rtk-docs/docs/usage/FEATURES.md` (command by command) plus `AI-Agents-Docs/rtk-docs/docs/guide/`; where the mirror and the installed 1.0.1 disagree, `rtk <cmd> --help` wins (they do disagree on `rtk read`'s default level). Config lives at `%APPDATA%\rtk\config.toml` and does not exist by default; `rtk config` prints the effective one.

### Rules

- Prefer `rtk` over the normal command when RTK provides an equivalent.
- Use the normal command when RTK does not provide an appropriate equivalent.
- Do not use RTK if the full/raw output is required for the task.
- Do not run both RTK and the normal command just to compare their output.
- RTK only filters/condenses output; it does not change the underlying command's intended behavior.
- If RTK hides information needed to continue, use `rtk recall` when applicable or run the normal command.

### Safety net (why prefixing is always safe)

- An unrecognized subcommand passes through unchanged (raw passthrough), so `rtk <anything>` can never break the command it wraps.
- `rtk bypass <cmd>` runs a command with no filtering at all (still tracked), for when the exact raw output matters.
- `RTK_DISABLED=1 <cmd>` bypasses RTK for a single invocation.
- Elided or failed output is not lost: RTK archives it and appends a recovery hint, for example `[full output: rtk recall 36365b69eda6]` or `[full diff: rtk git diff --no-compact]`. Follow the hint exactly as printed: `rtk recall <hash>` (a unique prefix of the hash is enough), `--full` for everything, `--grep PAT` to filter, `--list` to browse the store. Entries are kept 30 days, 10 MiB each.

### Common replacements

- `ls` → `rtk ls`
- `tree` → `rtk tree`
- `cat` / file reading → `rtk read`
- `find` → `rtk find`
- `grep` → `rtk grep`
- `rg` → `rtk rg`
- `git ...` → `rtk git ...`
- `gh ...` → `rtk gh ...`
- `curl ...` → `rtk curl ...`
- `wget ...` → `rtk wget ...`

Run `./gradlew` normally; RTK has no Gradle wrapper and the full output is the verification gate anyway.

### Everyday commands

| Command | Use when | Notes |
|---|---|---|
| `rtk ls`, `rtk tree` | directory listings | native flags pass through; a few combinations are rejected by rtk's own parser (seen with `rtk tree -L 4 -I <pattern>`: "Too many parameters"), fall back to plain `find`/`ls` instead of fighting the proxy |
| `rtk read <file>` | shell file reading (cat/head/tail) | `-l minimal` strips comments and excess blank lines, `-l aggressive` keeps signatures only, `-m N` is a structural preview capped at N lines that keeps signatures and imports (not the first N lines, use `--head-lines` for that), `--head-lines N`/`--tail-lines N` are byte-exact windows, `-n` adds line numbers, multiple files like `cat`. On installed 1.0.1 the default level is `none` (full content), not `minimal` as the mirror says |
| `rtk find` | file discovery | compact output grouped by directory; accepts native `find` flags (`-name`, `-type`) |
| `rtk wc` | line/word/byte counts | strips paths and padding |
| `rtk git <sub>` | all git work | compact `status`/`log`/`diff`/`show`/`add`/`commit`/`push`/`pull`/`branch`/`fetch`/`stash`/`worktree`; any other subcommand passes through untouched; global git options (`-C`, `-c`, `--no-pager`) work |
| `rtk gh <sub>` | GitHub CLI | `pr list`/`pr view`/`pr checks`, `issue list`, `run list`, `api` |
| `rtk curl`, `rtk wget` | HTTP and downloads | `rtk curl` truncates long bodies (archived for recall), `rtk wget` strips progress bars |
| `rtk json <file>` | JSON inspection | values compacted, `--keys-only` for shape only, `--depth N` caps depth, `-` reads stdin |
| `rtk env` | environment variables | secrets masked by default |
| `rtk log <file>` | log files, or stdin via pipe | deduplicates repeated lines into `error x42` counters |

Git output gotchas:

- `rtk git diff` is condensed and **not an applicable patch**: the `diff --git`/`---`/`+++` headers are stripped, so never pipe it into `git apply`. For a faithful patch use plain `git diff` or `rtk bypass git diff`. Truncated output ends with a per-sign note plus the `--no-compact` hint.
- `rtk git show` windows large blobs: `rtk git show HEAD:bigfile > out` can silently truncate while still exiting 0. Capture big blobs with plain `git show` or follow the printed recovery hint.
- `rtk git add`/`commit`/`push` answer in one line (`ok`, `ok <short hash>`): that one word is success, not lost output.

### Command runners

- `rtk test <cmd>`: runs any test command, keeps only the failures plus a `FAILED: n/m` summary line. Use when only test results matter.
- `rtk err <cmd>`: runs any command, keeps only errors and warnings.
- `rtk summary <cmd>`: runs any command, prints a heuristic summary of its output; useful for long-running commands with no dedicated filter.
- `rtk smart <file>`: a 2-line heuristic summary of a source file.
- `rtk diff <f1> <f2>`: condensed two-file diff, changed lines only; exit code 0 same, 1 different, 2 unreadable. `rtk diff -` condenses a unified diff read on stdin.
- The command runs directly (no shell interpretation of globs, variables, or operators) unless `--shell '<whole command>'` is passed.

### Useful specialized commands

- Use `rtk test` when only test failures/results are needed.
- Use `rtk err` when only errors and warnings are relevant.
- Use `rtk diff` for a compact diff when the full diff is unnecessary.
- Use `rtk json` when inspecting JSON output.
- Use `rtk summary` or `rtk smart` when a concise command summary is useful.

Do not blindly replace every command with RTK; if RTK's filtering could hide information needed to continue, run the normal command.

## ripgrep

`rg` 15.2.0 (PCRE2 build, real `.exe` on PATH via WinGet) is the default content-search tool: `rg -n "pattern" path`. `rtk rg` compacts the output; prefer plain `rg` directly for content search, reach for `rtk rg` when a broad sweep would dump hundreds of lines. Full guide: `AI-Agents-Docs/ripgrep-docs/GUIDE.md`.

### What it searches by default, and what it silently skips

Recursive from the given path (cwd if none given), line numbers on. It silently skips: gitignored files (`.gitignore`, `.ignore`, `.rgignore`, `$GIT_DIR/info/exclude`, and `core.excludesFile` globs all count), hidden files and directories, binary files (a file containing any NUL byte is binary), and symlinks (not followed). "No matches" usually means the ignore rules, not the code: retry with `-uu` (also hidden) or `-uuu` (also binary) before concluding anything. Escapes: `-u` drops gitignore handling, `--no-ignore`, `--hidden` (short `-.`), `-a`/`--text` (search binary as text), `-L`/`--follow` (symlinks). `rg --debug` explains why a file was skipped; `rg --files` lists what would be searched without searching anything.

### Pattern flags that matter

| Flag | Effect |
|---|---|
| `-F` | literal string, no regex; use when the pattern is full of `.`, `(`, `[` and you mean them literally |
| `-w` | whole-word match |
| `-i` / `-S` | case-insensitive / smart case (insensitive unless the pattern contains uppercase) |
| `-e PAT` | explicit pattern, needed when the pattern starts with `-` |
| `-v` | invert match |
| `-U` | multiline matching (patterns spanning lines) |
| `-c` / `-l` | count of matched lines / only the file names |
| `-o` | print only the matched part |
| `-C n` / `-B n` / `-A n` | n context lines around / before / after each match |
| `-M n` | cap printed line length |
| `-z` | search inside compressed files (gzip, xz, zstd, ...) |
| `--sort path` | deterministic output order, disables parallelism |

### Narrowing the file set

- Globs: `-g '*.java'` includes, `-g '!*.html'` excludes. Globs are gitignore-style and a later glob overrides an earlier one. Quote globs in single quotes so the shell does not expand the `*`.
- Types: `-t java` includes the type, `-T java` excludes it; `rg --type-list` shows every built-in type and its globs.

### Output rewriting

`-r 'replacement'` rewrites the matched text in the printed output only: ripgrep never modifies files, there is no in-place replace mode. Capture groups work, `-r '$1'` for the first group, named groups `(?P<name>...)` with `-r '$name'`; combine with `-o` to print only the rewritten matches.

## uutils coreutils

uutils/coreutils is a Rust rewrite of the GNU coreutils (universal, cross-platform CLI utilities, available for Linux, Windows, macOS), installed via WinGet as real `.exe` shims: `head`, `tail`, `wc`, `sort`, `tr`, `cut`, `seq`, `od`, `basename`, `dirname`, `realpath`, `touch`, `tee`, and the rest of the coreutils set. The per-util manual sits at `AI-Agents-Docs/uutils_docs/uutils.org/coreutils/docs/utils/<util>.html` (for example `cp.html`, `xargs.html`), with the index at `docs/index.html` next to it. The Git Bash shadowing below means interactive basics actually run as GNU 8.32; consult the uutils page when a shim in PowerShell/CMD rejects a flag, or before reaching for a less common util, the pages document exact CLI compatibility per tool.

## mdka

`mdka` converts HTML to Markdown. Its purpose in this repo: the vendored Paper docs (`AI-Agents-Docs/papermc_dev_docs/...`) are HTML, and a converted `.md` is far cheaper to Read than the raw page. Docs mirror: `AI-Agents-Docs/mdka_rs_docs/` (the 3.x site, matches 3.3.0's mode list and removal behavior).

`mdka` 3.3.0 is the only install, at `%USERPROFILE%\.local\bin\mdka.exe`, and bare `mdka` resolves to it.

### Usage (3.3.0 at `~/.local/bin/mdka`)

- stdin: `cat page.html | mdka > page.md`; progress and errors go to stderr, so stdout carries only the markdown.
- single file: `mdka page.html` writes `page.md` beside the input and prints nothing to stdout.
- **GOTCHA:** `mdka page.html > out.md` produces an EMPTY `out.md`: the file-argument form writes beside the input, so the redirect captures nothing. Choose the destination with `-o`: `mdka -o out/ page.html`.
- bulk: `-o` is required when converting multiple files: `mdka -o out/ docs/*.html`.
- modes (`-m`): `balanced` (default) and `minimal` (body text and structure only, already without shell elements and id anchors, the LLM-reading mode). 3.x removed `strict`/`semantic`/`preserve` and the deprecated no-effect flags (`--preserve-classes`, `--preserve-data`, `--preserve-aria`, `--unwrap-wrappers`); 3.3.0 exits 1 with a naming error for each.
- `--drop-shell` drops `nav`/`header`/`footer`/`aside` (only needed for `balanced`, `minimal` already excludes them); `--no-preserve-ids` turns off the `<a id>` anchor emission (anchors are on by default except in `minimal`).
- 3.3.0 extras the mirror does not mention yet: `--emphasis-from-style` (an inline style attribute may add bold/italic, default off) and `--backslash-hard-breaks` (hard break as a backslash instead of two trailing spaces, default off). Where mirror and binary disagree, `mdka --help` wins.

The recipe for vendored doc pages: `mdka -m minimal -o <dir> page.html`, then Read the produced `.md`.

Unknown `--flags` are rejected rather than treated as filenames; a file whose name starts with `-` needs `--` first: `mdka -- -weird.html`.

## Shell tools on this Windows machine

The session shell is Git Bash; what a command name resolves to depends on the shell, which matters when a flag suddenly "does not exist".

- **ripgrep (`rg`)** and **uutils/coreutils** are real `.exe`s on PATH (both via WinGet), see their sections above.
- **`mdka`** is the 3.3.0 in `%USERPROFILE%\.local\bin`; no other install exists anymore.
- Inside a Git Bash session the GNU coreutils 8.32 in `/usr/bin` shadow the uutils shims, so the basics behave as GNU; the uutils `.exe`s win in PowerShell/CMD. Behavior-compatible for the documented basics.
- PowerShell built-ins shadow some of those names inside a PowerShell session (`ls`, `cat`, `sort`, `cp`, `mv`, `rm`, `echo`, `pwd`, `mkdir`, `sleep`, `test`): there they resolve to the PS cmdlets, whose flags differ from GNU (e.g. `cat --version` fails). Spawned subprocesses and non-PowerShell contexts see the uutils `.exe`s. If a tool "is not on PATH" in a fresh shell, restart PowerShell or dot-source the profile (`. $PROFILE`).
- `find` inside Git Bash is GNU find (see the nuance above); in shells without Git's `/usr/bin` on PATH it resolves to Windows `find.exe`, not GNU find. Use `rg --files` or `Get-ChildItem -Recurse -Filter` for file discovery there.
