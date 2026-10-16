import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import update_check


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wd-update-test-"))
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp)
        update_check._pending_notice = None

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_version_compare_is_numeric(self):
        self.assertEqual(update_check._parse_version("v2.10.0"), (2, 10, 0))
        self.assertGreater(
            update_check._parse_version("v2.10.0"),
            update_check._parse_version("v2.9.0"),
        )
        self.assertIsNone(update_check._parse_version("v2.9.0-beta"))
        self.assertIsNone(update_check._parse_version("release"))

    def test_check_notifies_on_newer_version(self):
        state = self.tmp / "state"
        original_state = update_check._state_path
        original_release = update_check._latest_release
        update_check._state_path = lambda: state / "update-check.json"
        update_check._latest_release = lambda: (
            "v99.0.0",
            "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/v99.0.0",
        )
        try:
            update_check._check()
        finally:
            update_check._state_path = original_state
            update_check._latest_release = original_release

        self.assertEqual(
            update_check.take_notice(),
            (
                "v99.0.0",
                "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/v99.0.0",
            ),
        )
        self.assertIsNone(update_check.take_notice())
        self.assertEqual(
            json.loads((state / "update-check.json").read_text())["last_notified"],
            "v99.0.0",
        )

    def test_check_stays_silent_for_same_version(self):
        state = self.tmp / "state"
        original_state = update_check._state_path
        original_release = update_check._latest_release
        update_check._state_path = lambda: state / "update-check.json"
        update_check._latest_release = lambda: (
            "v" + self._running_version(),
            "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/x",
        )
        try:
            update_check._check()
        finally:
            update_check._state_path = original_state
            update_check._latest_release = original_release

        self.assertIsNone(update_check.take_notice())
        self.assertFalse(state.exists())

    def test_notified_version_is_mentioned_only_once(self):
        state = self.tmp / "state"
        original_state = update_check._state_path
        original_release = update_check._latest_release
        update_check._state_path = lambda: state / "update-check.json"
        update_check._latest_release = lambda: (
            "v99.0.0",
            "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/v99.0.0",
        )
        try:
            update_check._check()
            self.assertIsNotNone(update_check.take_notice())
            update_check._check()
        finally:
            update_check._state_path = original_state
            update_check._latest_release = original_release

        self.assertIsNone(update_check.take_notice())

    def test_latest_release_rejects_foreign_url(self):
        body = json.dumps(
            {
                "tag_name": "v9.0.0",
                "html_url": "https://evil.example.com/repo/releases/tag/v9.0.0",
            }
        ).encode()

        original_open = update_check.urllib.request.urlopen
        update_check.urllib.request.urlopen = lambda request, timeout: io.BytesIO(body)
        try:
            release = update_check._latest_release()
        finally:
            update_check.urllib.request.urlopen = original_open

        self.assertIsNone(release)

    def test_latest_release_accepts_project_url(self):
        body = json.dumps(
            {
                "tag_name": "v9.0.0",
                "html_url": "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/v9.0.0",
            }
        ).encode()

        original_open = update_check.urllib.request.urlopen
        update_check.urllib.request.urlopen = lambda request, timeout: io.BytesIO(body)
        try:
            release = update_check._latest_release()
        finally:
            update_check.urllib.request.urlopen = original_open

        self.assertEqual(
            release,
            (
                "v9.0.0",
                "https://github.com/Mitra-88/WorkshopDecompressor/releases/tag/v9.0.0",
            ),
        )

    def test_start_skipped_without_tty(self):
        with (
            mock.patch.object(sys, "stdout", io.StringIO()),
            mock.patch.object(update_check.threading, "Thread") as thread,
        ):
            update_check.start()

        thread.assert_not_called()

    def test_start_skipped_when_opt_out_set(self):
        with (
            mock.patch.dict(os.environ, {update_check.OPT_OUT_ENV: "1"}),
            mock.patch.object(update_check.threading, "Thread") as thread,
        ):
            update_check.start()

        thread.assert_not_called()

    def test_start_runs_thread_in_tty(self):
        fake_stdout = mock.Mock()
        fake_stdout.isatty.return_value = True

        with (
            mock.patch.object(update_check.threading, "Thread") as thread,
            mock.patch.object(sys, "stdout", fake_stdout),
        ):
            update_check.start()

        thread.assert_called_once()

    @staticmethod
    def _running_version():
        from utils import APP_VERSION

        return APP_VERSION


if __name__ == "__main__":
    unittest.main()
