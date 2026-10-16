import hashlib
import json
import logging
import os
import platform
import shutil
import stat
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from contextlib import nullcontext
from pathlib import Path
from subprocess import DEVNULL, SubprocessError, run

import ui

logger = logging.getLogger("workshop.executables")

TOOL_RELEASE_REPOS = {
    "7z": "Mitra-88/7zip",
    "fastgmad": "Mitra-88/fastgmad",
}

_OS_KEYWORDS = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}

_API_TIMEOUT = 20
_DOWNLOAD_TIMEOUT = 60
_DOWNLOAD_RETRIES = 3
_RETRY_DELAY = 2
_CHUNK_SIZE = 64 * 1024
_SMOKE_TEST_TIMEOUT = 10


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundled_bin_dir(system):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "Bin" / system
    return None


def _executables_for(system):
    return {
        "7z": "7zz.exe" if system == "Windows" else "7zz",
        "fastgmad": "fastgmad.exe" if system == "Windows" else "fastgmad",
    }


def _open_url(url, timeout):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "WorkshopDecompressor", "Accept": "*/*"},
    )
    return urllib.request.urlopen(request, timeout=timeout)


def _fetch_release_asset(repo, system_keyword):
    """Return (url, algo, hash_hex, size) for the one OS asset of the nightly release."""
    url = f"https://api.github.com/repos/{repo}/releases/tags/nightly"

    for attempt in range(_DOWNLOAD_RETRIES):
        try:
            with _open_url(url, _API_TIMEOUT) as response:
                release = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 and attempt < _DOWNLOAD_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
                continue
            logger.warning(
                "GitHub returned %s for the %s nightly release. Not retrying: "
                "403 usually means the unauthenticated rate limit is used up.",
                exc.code,
                repo,
            )
            return None
        except urllib.error.URLError, TimeoutError, OSError:
            if attempt < _DOWNLOAD_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
                continue
            logger.warning("Could not reach GitHub for the %s nightly release.", repo)
            return None

    matches = [
        asset
        for asset in release.get("assets", [])
        if system_keyword in asset.get("name", "").lower()
    ]

    if len(matches) != 1:
        logger.warning(
            "Expected exactly one %s asset on the %s nightly release, found %d.",
            system_keyword,
            repo,
            len(matches),
        )
        return None

    asset = matches[0]
    digest = asset.get("digest") or ""
    size = asset.get("size") or 0
    algo, _, expected_hash = digest.partition(":")

    if algo not in ("sha256", "sha512") or not expected_hash or not size:
        logger.warning(
            "The %s nightly asset has no sha256 or sha512 digest or size, "
            "refusing to download it.",
            repo,
        )
        return None

    return asset["browser_download_url"], algo, expected_hash, size


def _download_verified(
    url, algo, expected_hash, expected_size, temp_path, progress_factory=None
):
    """Stream url to temp_path, verifying size and checksum while bytes arrive."""
    progress_factory = progress_factory or (
        lambda description, total: nullcontext(lambda step: None)
    )

    for attempt in range(_DOWNLOAD_RETRIES):
        hasher = hashlib.new(algo)
        received = 0

        try:
            with (
                _open_url(url, _DOWNLOAD_TIMEOUT) as response,
                open(temp_path, "wb") as out,
                progress_factory(Path(url).name, expected_size) as advance,
            ):
                while chunk := response.read(_CHUNK_SIZE):
                    hasher.update(chunk)
                    received += len(chunk)
                    out.write(chunk)
                    advance(len(chunk))
        except urllib.error.HTTPError as exc:
            temp_path.unlink(missing_ok=True)
            if exc.code >= 500 and attempt < _DOWNLOAD_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
                continue
            logger.warning("Could not download the tool bundle (HTTP %s).", exc.code)
            return False
        except urllib.error.URLError, TimeoutError, OSError:
            temp_path.unlink(missing_ok=True)
            if attempt < _DOWNLOAD_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
                continue
            logger.warning("Could not download the tool bundle from GitHub.")
            return False

        if received != expected_size or hasher.hexdigest() != expected_hash:
            temp_path.unlink(missing_ok=True)
            logger.warning(
                "The download did not match the published checksum and size "
                "(got %d bytes), it was deleted.",
                received,
            )
            return False

        return True

    return False


def _extract_tool(archive_path, member_name, dest_path):
    """Extract one regular file by basename from a zip or tar.gz, atomically."""
    temp_path = dest_path.with_name(dest_path.name + ".part")

    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as bundle:
                match = next(
                    (
                        info
                        for info in bundle.infolist()
                        if not info.is_dir() and Path(info.filename).name == member_name
                    ),
                    None,
                )

                if match is None:
                    return False

                with bundle.open(match) as src, open(temp_path, "wb") as out:
                    shutil.copyfileobj(src, out)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as bundle:
                match = next(
                    (
                        member
                        for member in bundle.getmembers()
                        if member.isfile() and Path(member.name).name == member_name
                    ),
                    None,
                )

                if match is None:
                    return False

                with bundle.extractfile(match) as src, open(temp_path, "wb") as out:
                    shutil.copyfileobj(src, out)
        else:
            return False
    except OSError, tarfile.TarError, zipfile.BadZipFile:
        temp_path.unlink(missing_ok=True)
        return False

    os.replace(temp_path, dest_path)
    return True


def _runs_on_this_cpu(exe_path):
    """Run the tool's help flag; a binary built for a newer CPU crashes or exits oddly."""
    try:
        result = run(
            [str(exe_path), "--help"],
            capture_output=True,
            timeout=_SMOKE_TEST_TIMEOUT,
            check=False,
        )
    except OSError, SubprocessError:
        return False

    return result.returncode == 0 or bool(
        result.stdout.strip() or result.stderr.strip()
    )


def _recover_missing_tools(missing, bin_dir, progress_factory=None):
    """Download missing tools from their nightly releases. Returns the paths recovered."""
    system = platform.system()
    system_keyword = _OS_KEYWORDS[system]
    filenames = _executables_for(system)
    recovered = {}

    for name in missing:
        repo = TOOL_RELEASE_REPOS.get(name)

        if repo is None:
            continue

        logger.info("Looking up %s on the %s nightly release...", name, repo)
        asset = _fetch_release_asset(repo, system_keyword)

        if asset is None:
            continue

        url, algo, expected_hash, expected_size = asset
        temp_archive = bin_dir / f".{name}-download"

        try:
            logger.info("Downloading %s...", Path(url).name)

            if not _download_verified(
                url,
                algo,
                expected_hash,
                expected_size,
                temp_archive,
                progress_factory,
            ):
                continue

            logger.info("Checksum verified, extracting the tool...")
            filename = filenames[name]

            if not _extract_tool(temp_archive, filename, bin_dir / filename):
                logger.warning(
                    "The %s nightly bundle did not contain %s.", repo, filename
                )
                continue
        finally:
            temp_archive.unlink(missing_ok=True)

        logger.info("Checking that %s runs on this CPU...", filename)

        if not _runs_on_this_cpu(bin_dir / filename):
            logger.warning(
                "%s was downloaded but would not run on this CPU and was removed. "
                "It may need a newer processor (AVX2). Use the manual path option instead.",
                filename,
            )
            (bin_dir / filename).unlink(missing_ok=True)
            continue

        recovered[name] = str(bin_dir / filename)
        logger.info("Installed %s successfully.", filename)

    return recovered


def prepare_executables(exec_paths):
    system = platform.system()
    if system not in ("Linux", "Darwin"):
        return

    for name, executable_path in exec_paths.items():
        try:
            path = Path(executable_path)
            os.chmod(path, path.stat().st_mode | stat.S_IEXEC)
        except OSError as exc:
            logger.warning(
                "Could not mark %s as executable. If it fails to run, check permissions. Reason: %s",
                name,
                exc,
            )

        if system == "Darwin":
            try:
                run(
                    ["xattr", "-d", "com.apple.quarantine", str(path)],
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                    check=False,
                )
            except OSError as exc:
                logger.warning(
                    "Could not clear the macOS quarantine flag on %s. If macOS refuses to open it, right-click it and choose Open. Reason: %s",
                    name,
                    exc,
                )


def _display_path(path):
    try:
        return path.relative_to(_get_base_dir()).as_posix()
    except ValueError:
        return path.as_posix()


def locate_executables():
    system = platform.system()
    bin_dir = _get_base_dir() / "Bin" / system
    bundled_bin_dir = _bundled_bin_dir(system)

    found = {}
    missing = []
    rows = []

    for name, filename in _executables_for(system).items():
        expected_path = bin_dir / filename
        full_path = expected_path
        exists = full_path.is_file()

        if not exists and bundled_bin_dir is not None:
            bundled_path = bundled_bin_dir / filename
            if bundled_path.is_file():
                full_path = bundled_path
                exists = True

        rows.append(
            {
                "name": name,
                "path": _display_path(expected_path),
                "found": exists,
            }
        )

        if exists:
            found[name] = str(full_path)
        else:
            missing.append(name)

    return found, missing, rows, bin_dir


def ensure_executable_paths():
    found, missing, rows, bin_dir = locate_executables()

    ui.render_rule("Tool Setup")
    ui.render_tool_status(rows)

    if not missing:
        ui.render_spacer()
        ui.render_message(
            "Success! All required tools were found automatically.",
            "success",
        )
        ui.render_spacer()
        prepare_executables(found)
        return found

    ui.render_missing_tools_panel(missing)
    ui.render_directory_status(bin_dir)
    ui.render_spacer()

    if ui.confirm_continue(
        "Download tools",
        (
            "The missing tools can be downloaded from the project's nightly releases:",
            f"Missing: {', '.join(missing)}",
        ),
    ):
        downloaded = _recover_missing_tools(missing, bin_dir, ui.download_progress)

        if downloaded:
            found.update(downloaded)
            missing = [name for name in missing if name not in downloaded]

    if missing:
        manual_paths = ui.prompt_absolute_paths(missing)
        found.update(manual_paths)

    prepare_executables(found)

    return found
