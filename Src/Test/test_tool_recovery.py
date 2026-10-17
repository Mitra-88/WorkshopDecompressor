import hashlib
import io
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from subprocess import SubprocessError
from unittest import mock

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import get_executable

FAKE_EXE = b"MZ fake executable bytes"


class ToolRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wd-recovery-test-"))
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_zip(self, members):
        path = self.tmp / "bundle.zip"

        with zipfile.ZipFile(path, "w") as bundle:
            for name, data in members.items():
                bundle.writestr(name, data)

        return path

    def _make_tar_gz(self, members):
        path = self.tmp / "bundle.tar.gz"

        with tarfile.open(path, "w:gz") as bundle:
            for name, data in members.items():
                if data is None:
                    info = tarfile.TarInfo(name)
                    info.type = tarfile.DIRTYPE
                    bundle.addfile(info)
                else:
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    bundle.addfile(info, io.BytesIO(data))

        return path

    def test_extracts_exe_from_zip_root(self):
        archive = self._make_zip({"fastgmad.exe": FAKE_EXE, "LICENSE": b"mit"})
        dest = self.tmp / "fastgmad.exe"

        self.assertTrue(get_executable._extract_tool(archive, "fastgmad.exe", dest))
        self.assertEqual(dest.read_bytes(), FAKE_EXE)

    def test_extracts_exe_nested_in_subfolder(self):
        archive = self._make_zip({"docs/old/fastgmad.exe": FAKE_EXE})
        dest = self.tmp / "fastgmad.exe"

        self.assertTrue(get_executable._extract_tool(archive, "fastgmad.exe", dest))
        self.assertEqual(dest.read_bytes(), FAKE_EXE)

    def test_missing_member_fails(self):
        archive = self._make_zip({"other.exe": FAKE_EXE})

        self.assertFalse(
            get_executable._extract_tool(archive, "fastgmad.exe", self.tmp / "out")
        )
        self.assertFalse((self.tmp / "out").exists())

    def test_tar_directory_member_with_target_name_is_skipped(self):
        archive = self._make_tar_gz(
            {"fastgmad": None, "bin/fastgmad": FAKE_EXE, "notes.txt": b"n"}
        )
        dest = self.tmp / "fastgmad"

        self.assertTrue(get_executable._extract_tool(archive, "fastgmad", dest))
        self.assertEqual(dest.read_bytes(), FAKE_EXE)
        self.assertFalse(dest.with_name(dest.name + ".part").exists())

    def test_tar_with_only_directory_member_fails(self):
        archive = self._make_tar_gz({"fastgmad": None})

        self.assertFalse(
            get_executable._extract_tool(archive, "fastgmad", self.tmp / "out")
        )

    def test_fetch_release_asset_selects_os_asset(self):
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        release = {
            "assets": [
                {
                    "name": "Tool-linux-x64-abc.tar.gz",
                    "size": 1,
                    "digest": "sha256:aa",
                    "browser_download_url": "https://example/linux.tar.gz",
                },
                {
                    "name": "Tool-Windows-x64-v3-abc.zip",
                    "size": 1234,
                    "digest": "sha256:bb",
                    "browser_download_url": "https://example/win.zip",
                },
                {
                    "name": "Tool-macos-arm64-abc.tar.gz",
                    "size": 3,
                    "digest": "sha256:cc",
                    "browser_download_url": "https://example/mac.tar.gz",
                },
            ]
        }

        original = get_executable._open_url
        get_executable._open_url = lambda url, timeout: FakeResponse(
            b'{"assets": ' + __import__("json").dumps(release["assets"]).encode() + b"}"
        )
        try:
            asset = get_executable._fetch_release_asset("owner/repo", "windows")
        finally:
            get_executable._open_url = original

        self.assertEqual(asset, ("https://example/win.zip", "sha256", "bb", 1234))

    def test_fetch_release_asset_accepts_sha512(self):
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        body = b'{"assets": [{"name": "Tool-windows-x64.zip", "size": 10, "digest": "sha512:dd", "browser_download_url": "https://example/w.zip"}]}'
        original = get_executable._open_url
        get_executable._open_url = lambda url, timeout: FakeResponse(body)
        try:
            asset = get_executable._fetch_release_asset("owner/repo", "windows")
        finally:
            get_executable._open_url = original

        self.assertEqual(asset, ("https://example/w.zip", "sha512", "dd", 10))

    def test_download_verifies_sha512(self):
        payload = b"bundle-bytes-here"
        temp_path = self.tmp / "download.bin"
        good_hash = hashlib.sha512(payload).hexdigest()

        original = get_executable._open_url
        get_executable._open_url = lambda url, timeout: io.BytesIO(payload)
        try:
            ok = get_executable._download_verified(
                "https://example/bundle.zip",
                "sha512",
                good_hash,
                len(payload),
                temp_path,
            )
        finally:
            get_executable._open_url = original

        self.assertTrue(ok)
        self.assertEqual(temp_path.read_bytes(), payload)

        get_executable._open_url = lambda url, timeout: io.BytesIO(payload)
        try:
            bad = get_executable._download_verified(
                "https://example/bundle.zip",
                "sha512",
                "f" * 128,
                len(payload),
                temp_path,
            )
        finally:
            get_executable._open_url = original

        self.assertFalse(bad)
        self.assertFalse(temp_path.exists())

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        body = b'{"assets": [{"name": "Tool-windows-x64.zip", "size": 10, "browser_download_url": "https://example/w.zip"}]}'
        original = get_executable._open_url
        get_executable._open_url = lambda url, timeout: FakeResponse(body)
        try:
            asset = get_executable._fetch_release_asset("owner/repo", "windows")
        finally:
            get_executable._open_url = original

        self.assertIsNone(asset)

    def test_fetch_release_asset_403_is_not_retried(self):
        calls = []

        def failing_open(url, timeout):
            calls.append(url)
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)

        original = get_executable._open_url
        get_executable._open_url = failing_open
        try:
            asset = get_executable._fetch_release_asset("owner/repo", "windows")
        finally:
            get_executable._open_url = original

        self.assertIsNone(asset)
        self.assertEqual(len(calls), 1)

    def test_recover_missing_tools_installs_and_reports(self):
        archive = self._make_zip({"fastgmad.exe": FAKE_EXE})

        original_fetch = get_executable._fetch_release_asset
        original_download = get_executable._download_verified
        original_smoke = get_executable._startup_failure

        get_executable._fetch_release_asset = lambda repo, keyword: (
            "https://example/bundle.zip",
            "sha256",
            "0" * 64,
            100,
        )

        def fake_download(
            url, algo, expected_hash, expected_size, temp_path, progress_factory=None
        ):
            shutil.copyfile(archive, temp_path)
            return True

        get_executable._download_verified = fake_download
        get_executable._startup_failure = lambda exe: None
        try:
            recovered = get_executable._recover_missing_tools(["fastgmad"], self.tmp)
        finally:
            get_executable._fetch_release_asset = original_fetch
            get_executable._download_verified = original_download
            get_executable._startup_failure = original_smoke

        self.assertEqual(recovered, {"fastgmad": str(self.tmp / "fastgmad.exe")})
        self.assertTrue((self.tmp / "fastgmad.exe").exists())
        self.assertFalse((self.tmp / ".fastgmad-download").exists())

    def test_recover_rolls_back_when_smoke_test_fails(self):
        archive = self._make_zip({"fastgmad.exe": FAKE_EXE})

        original_fetch = get_executable._fetch_release_asset
        original_download = get_executable._download_verified
        original_smoke = get_executable._startup_failure

        get_executable._fetch_release_asset = lambda repo, keyword: (
            "https://example/bundle.zip",
            "sha256",
            "0" * 64,
            100,
        )
        get_executable._download_verified = (
            lambda url, algo, expected_hash, expected_size, temp_path, progress_factory=None: (
                shutil.copyfile(archive, temp_path) or True
            )
        )
        get_executable._startup_failure = lambda exe: "it stopped right away"
        try:
            recovered = get_executable._recover_missing_tools(["fastgmad"], self.tmp)
        finally:
            get_executable._fetch_release_asset = original_fetch
            get_executable._download_verified = original_download
            get_executable._startup_failure = original_smoke

        self.assertEqual(recovered, {})
        self.assertFalse((self.tmp / "fastgmad.exe").exists())

    def test_recover_falls_back_when_download_fails(self):
        original_fetch = get_executable._fetch_release_asset
        original_download = get_executable._download_verified

        get_executable._fetch_release_asset = lambda repo, keyword: (
            "https://example/bundle.zip",
            "sha256",
            "0" * 64,
            100,
        )
        get_executable._download_verified = (
            lambda url, algo, expected_hash, expected_size, temp_path, progress_factory=None: (
                False
            )
        )
        try:
            recovered = get_executable._recover_missing_tools(["fastgmad"], self.tmp)
        finally:
            get_executable._fetch_release_asset = original_fetch
            get_executable._download_verified = original_download

        self.assertEqual(recovered, {})

    def test_recover_creates_missing_bin_dir(self):
        archive = self._make_zip({"fastgmad.exe": FAKE_EXE})
        bin_dir = self.tmp / "deep" / "Bin" / platform.system()

        original_fetch = get_executable._fetch_release_asset
        original_download = get_executable._download_verified
        original_smoke = get_executable._startup_failure

        get_executable._fetch_release_asset = lambda repo, keyword: (
            "https://example/bundle.zip",
            "sha256",
            "0" * 64,
            100,
        )

        def fake_download(
            url, algo, expected_hash, expected_size, temp_path, progress_factory=None
        ):
            shutil.copyfile(archive, temp_path)
            return True

        get_executable._download_verified = fake_download
        get_executable._startup_failure = lambda exe: None
        try:
            recovered = get_executable._recover_missing_tools(["fastgmad"], bin_dir)
        finally:
            get_executable._fetch_release_asset = original_fetch
            get_executable._download_verified = original_download
            get_executable._startup_failure = original_smoke

        self.assertEqual(recovered, {"fastgmad": str(bin_dir / "fastgmad.exe")})

    def test_fetch_release_asset_rejects_non_json_response(self):
        original_open = get_executable._open_url
        get_executable._open_url = lambda url, timeout: io.BytesIO(
            b"<html>portal</html>"
        )
        try:
            asset = get_executable._fetch_release_asset("owner/repo", "windows")
        finally:
            get_executable._open_url = original_open

        self.assertIsNone(asset)

    def test_os_keyword_covers_this_platform(self):
        system = platform.system()

        self.assertIn(system, get_executable._OS_KEYWORDS)


class ToolResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wd-resolution-test-"))
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _locate_with(self, base_dir, meipass):
        original_base = get_executable._get_base_dir
        get_executable._get_base_dir = lambda: base_dir
        try:
            with mock.patch.object(sys, "_MEIPASS", str(meipass), create=True):
                return get_executable.locate_executables()
        finally:
            get_executable._get_base_dir = original_base

    def test_bundled_meipass_fallback_when_missing_beside_exe(self):
        system = platform.system()
        exe_name = get_executable._executables_for(system)["fastgmad"]
        base_dir = self.tmp / "app"
        meipass = self.tmp / "meipass"
        (meipass / "Bin" / system).mkdir(parents=True)
        (meipass / "Bin" / system / exe_name).write_bytes(FAKE_EXE)

        found, missing, rows, _bin_dir = self._locate_with(base_dir, meipass)

        self.assertNotIn("fastgmad", missing)
        self.assertIn("7z", missing)
        self.assertEqual(found["fastgmad"], str(meipass / "Bin" / system / exe_name))

        row = next(r for r in rows if r["name"] == "fastgmad")
        self.assertTrue(row["found"])
        self.assertEqual(
            row["path"],
            (base_dir / "Bin" / system / exe_name).relative_to(base_dir).as_posix(),
        )

    def test_beside_exe_wins_over_bundled(self):
        system = platform.system()
        exe_name = get_executable._executables_for(system)["fastgmad"]
        base_dir = self.tmp / "app"
        persistent = base_dir / "Bin" / system
        persistent.mkdir(parents=True)
        (persistent / exe_name).write_bytes(b"persistent")
        meipass = self.tmp / "meipass"
        (meipass / "Bin" / system).mkdir(parents=True)
        (meipass / "Bin" / system / exe_name).write_bytes(b"bundled")

        found, _missing, _rows, _bin_dir = self._locate_with(base_dir, meipass)

        self.assertEqual(found["fastgmad"], str(persistent / exe_name))

    def test_bundled_dir_is_none_without_meipass(self):
        if hasattr(sys, "_MEIPASS"):
            self.skipTest("running inside a PyInstaller bundle")

        self.assertIsNone(get_executable._bundled_bin_dir(platform.system()))


class StartupCheckTests(unittest.TestCase):
    def _completed(self, returncode, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_zero_exit_passes(self):
        with mock.patch.object(get_executable, "run", return_value=self._completed(0)):
            self.assertIsNone(get_executable._startup_failure("7zz"))

    def test_output_passes_even_with_error_code(self):
        with mock.patch.object(
            get_executable, "run", return_value=self._completed(2, stdout="FastGMAD")
        ):
            self.assertIsNone(get_executable._startup_failure("fastgmad"))

    def test_silent_crash_reports_the_exit_code(self):
        with mock.patch.object(
            get_executable, "run", return_value=self._completed(-1073741795)
        ):
            self.assertEqual(
                get_executable._startup_failure("7zz"),
                "it stopped right away with exit code -1073741795",
            )

    def test_unstartable_binary_reports_its_own_reason(self):
        with mock.patch.object(get_executable, "run", side_effect=PermissionError):
            self.assertEqual(
                get_executable._startup_failure("7zz"), "it could not be started"
            )

    def test_timeout_reports_its_own_reason(self):
        with mock.patch.object(get_executable, "run", side_effect=SubprocessError):
            self.assertEqual(
                get_executable._startup_failure("7zz"),
                "it did not finish starting up",
            )


class ToolSetupTests(unittest.TestCase):
    located = (
        {"7z": "found/7zz"},
        [],
        [{"name": "7z", "path": "Bin/7zz", "found": True}],
        Path("Bin"),
    )

    def _run_setup(self, startup_failure):
        with (
            mock.patch.object(
                get_executable, "locate_executables", return_value=self.located
            ),
            mock.patch.object(get_executable, "prepare_executables"),
            mock.patch.object(
                get_executable, "_startup_failure", return_value=startup_failure
            ),
            mock.patch.object(get_executable.ui, "render_rule"),
            mock.patch.object(get_executable.ui, "render_tool_status"),
            mock.patch.object(get_executable.ui, "render_spacer"),
            mock.patch.object(get_executable.ui, "render_message"),
            mock.patch.object(
                get_executable.ui, "render_cpu_requirement_panel"
            ) as self.panel,
            mock.patch.object(
                get_executable.ui,
                "prompt_absolute_paths",
                return_value={"7z": "mine/7zz"},
            ) as self.prompt,
        ):
            return get_executable.ensure_executable_paths()

    def test_runnable_tool_skips_the_prompt(self):
        found = self._run_setup(None)

        self.assertEqual(found, {"7z": "found/7zz"})
        self.panel.assert_not_called()
        self.prompt.assert_not_called()

    def test_unusable_tool_is_asked_for_again_by_path(self):
        reason = "it stopped right away with exit code -4"
        found = self._run_setup(reason)

        self.panel.assert_called_once_with({"7z": reason})
        self.prompt.assert_called_once_with(["7z"])
        self.assertEqual(found, {"7z": "mine/7zz"})


if __name__ == "__main__":
    unittest.main()
