import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import utils

BUNDLED_FILE = "PyInstaller 1.2.3\nRich 4.5.6\n7-Zip (z) 26.04 (x64)\n"


class ToolVersionsTests(unittest.TestCase):
    def test_frozen_build_reads_bundled_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build_tools.txt").write_text(BUNDLED_FILE, encoding="utf-8")
            with (
                mock.patch.object(sys, "frozen", True, create=True),
                mock.patch.object(sys, "_MEIPASS", tmp, create=True),
            ):
                self.assertEqual(
                    utils._tool_versions(),
                    "PyInstaller 1.2.3, Rich 4.5.6, 7-Zip (z) 26.04 (x64)",
                )

    def test_frozen_build_without_bundled_file_falls_back(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(sys, "frozen", True, create=True),
            mock.patch.object(sys, "_MEIPASS", tmp, create=True),
        ):
            self.assertIn("7-Zip (bundled)", utils._tool_versions())

    def test_development_build_uses_installed_versions(self):
        versions = utils._tool_versions()
        self.assertIn("PyInstaller ", versions)
        self.assertIn("7-Zip (bundled)", versions)


if __name__ == "__main__":
    unittest.main()
