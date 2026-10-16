import os
import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import extract_addons
import extract_archives
from utils import (
    app_version,
    build_date,
    extraction_workers,
    get_system_info,
    join_parts,
    run_sevenzip_extraction,
)

TEST_DIR = Path(__file__).resolve().parent
SYSTEM = platform.system()
SEVEN_ZIP = (
    TEST_DIR.parent / "Bin" / SYSTEM / ("7zz.exe" if SYSTEM == "Windows" else "7zz")
)


class SevenZipDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wd-7z-test-"))
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sevenzip_warning_code_one_reports_warning(self):
        bin_copy = self.tmp / "Partial.bin"
        bin_copy.write_bytes(b"anything")
        (self.tmp / "Extracted-Bin").mkdir()

        original = extract_addons.run_sevenzip_extraction

        def fake_run(path, archive, output):
            (output / "file.txt").write_text("x")
            return True, 1, "some items had errors"

        extract_addons.run_sevenzip_extraction = fake_run
        try:
            outcome = extract_addons.extract_bin_file(bin_copy, "unused")
        finally:
            extract_addons.run_sevenzip_extraction = original

        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["returncode"], 1)
        self.assertIn("7-Zip reported", outcome["warning"])
        self.assertIn("incomplete", outcome["warning"])

    def test_archive_warning_code_one_reports_warning(self):
        archive_copy = self.tmp / "Partial.zip"
        archive_copy.write_bytes(b"anything")
        (self.tmp / "Leftover").mkdir()

        original = extract_archives.run_sevenzip_extraction

        def fake_run(path, archive, output):
            (output / "file.txt").write_text("x")
            return True, 1, "some items had errors"

        extract_archives.run_sevenzip_extraction = fake_run
        try:
            outcome = extract_archives.extract_archive(
                archive_copy, self.tmp / "Leftover", "unused"
            )
        finally:
            extract_archives.run_sevenzip_extraction = original

        self.assertTrue(outcome["success"])
        self.assertIn("7-Zip reported", outcome["warning"])
        self.assertTrue((self.tmp / "Leftover" / "Partial.zip").exists())

    def test_legacy_bin_with_trailing_data_reports_success(self):
        bin_copy = self.tmp / "Legacy-Addon.bin"
        bin_copy.write_bytes((TEST_DIR / "Legacy-Addon.bin").read_bytes())

        outcome = extract_addons.extract_bin_file(bin_copy, str(SEVEN_ZIP))

        self.assertTrue(outcome["success"], outcome["error"])
        self.assertEqual(outcome["returncode"], 2)
        self.assertIn("7-Zip reported", outcome["warning"])
        extracted_dir = next(self.tmp.glob("Extracted-Bin*"))
        extracted_files = [p for p in extracted_dir.iterdir() if p.is_file()]
        self.assertTrue(extracted_files)
        self.assertTrue(all(p.stat().st_size > 0 for p in extracted_files))

    def test_garbage_bin_reports_failure(self):
        bin_copy = self.tmp / "Garbage.bin"
        bin_copy.write_bytes(b"definitely not an archive")

        outcome = extract_addons.extract_bin_file(bin_copy, str(SEVEN_ZIP))

        self.assertFalse(outcome["success"])
        self.assertTrue(outcome["error"])
        extracted_dir = next(self.tmp.glob("Extracted-Bin*"))
        self.assertFalse(any(extracted_dir.iterdir()))

    def test_regular_sevenzip_archive_succeeds(self):
        archive_copy = self.tmp / "Sample.7z"
        archive_copy.write_bytes((TEST_DIR / "Sample.7z").read_bytes())
        out_dir = self.tmp / "out"
        out_dir.mkdir()

        extracted, returncode, _ = run_sevenzip_extraction(
            str(SEVEN_ZIP), archive_copy, out_dir
        )

        self.assertTrue(extracted)
        self.assertEqual(returncode, 0)

    def test_gma_extraction_still_works(self):
        fastgmad = (
            TEST_DIR.parent
            / "Bin"
            / SYSTEM
            / ("fastgmad.exe" if SYSTEM == "Windows" else "fastgmad")
        )
        gma_copy = self.tmp / "Modern-Addon.gma"
        gma_copy.write_bytes((TEST_DIR / "Modern-Addon.gma").read_bytes())

        outcome = extract_addons.extract_gma_file(gma_copy, str(fastgmad))

        self.assertTrue(outcome["success"], outcome["error"])
        self.assertEqual(outcome["returncode"], 0)

    def test_rar_routes_through_sevenzip(self):
        archive_copy = self.tmp / "Sample.rar"
        archive_copy.write_bytes((TEST_DIR / "Sample.rar").read_bytes())
        leftover = self.tmp / "Leftover"
        leftover.mkdir()

        outcome = extract_archives.extract_archive(
            archive_copy, leftover, str(SEVEN_ZIP)
        )

        self.assertTrue(outcome["success"], outcome["error"])
        extracted = [p for p in self.tmp.glob("Sample*/**/*") if p.is_file()]
        self.assertTrue(extracted)
        self.assertTrue((leftover / "Sample.rar").exists())

    def test_dotted_archive_name_gets_output_dir(self):
        archive_copy = self.tmp / "My.Addon.zip"
        archive_copy.write_bytes((TEST_DIR / "Sample.zip").read_bytes())
        leftover = self.tmp / "Leftover"
        leftover.mkdir()

        outcome = extract_archives.extract_archive(
            archive_copy, leftover, str(SEVEN_ZIP)
        )

        self.assertTrue(outcome["success"], outcome["error"])
        self.assertTrue(any(self.tmp.glob("My.Addon*/**")))

    def test_broken_archive_reports_failure(self):
        archive_copy = self.tmp / "Broken.7z"
        archive_copy.write_bytes(b"not an archive at all")
        leftover = self.tmp / "Leftover"
        leftover.mkdir()

        outcome = extract_archives.extract_archive(
            archive_copy, leftover, str(SEVEN_ZIP)
        )

        self.assertFalse(outcome["success"])
        self.assertTrue(outcome["error"])
        self.assertFalse((leftover / "Broken.7z").exists())

    def test_zip_and_tar_route_through_sevenzip(self):
        for name in ("Sample.zip", "Sample.tar"):
            archive_copy = self.tmp / name
            archive_copy.write_bytes((TEST_DIR / name).read_bytes())
            leftover = self.tmp / "Leftover"
            leftover.mkdir(exist_ok=True)

            outcome = extract_archives.extract_archive(
                archive_copy, leftover, str(SEVEN_ZIP)
            )

            self.assertTrue(outcome["success"], outcome["error"])
            self.assertTrue((leftover / name).exists())
            extracted = list(self.tmp.glob(f"{Path(name).stem}*/**/Sample.txt"))
            self.assertTrue(extracted, f"Sample.txt not extracted from {name}")

    def test_compound_tar_extracts_final_contents(self):
        for name in ("Sample.tar.gz", "Sample.tar.xz", "Sample.tar.bz2"):
            archive_copy = self.tmp / name
            archive_copy.write_bytes((TEST_DIR / name).read_bytes())
            leftover = self.tmp / "Leftover"
            leftover.mkdir(exist_ok=True)

            outcome = extract_archives.extract_archive(
                archive_copy, leftover, str(SEVEN_ZIP)
            )

            self.assertTrue(outcome["success"], outcome["error"])
            extracted = list(
                self.tmp.glob(f"{Path(name).stem.removesuffix('.tar')}*/**/Sample.txt")
            )
            self.assertTrue(extracted, f"Sample.txt not extracted from {name}")
            leftovers = list(leftover.glob("*.tar"))
            self.assertFalse(leftovers, f"intermediate tar left behind for {name}")

    def test_unwritable_output_folder_fails_fast(self):
        blocker = self.tmp / "Extracted-Addons"
        blocker.write_bytes(b"")
        (self.tmp / "Modern-Addon.gma").write_bytes(
            (TEST_DIR / "Modern-Addon.gma").read_bytes()
        )

        exec_paths = {
            "7z": str(SEVEN_ZIP),
            "fastgmad": str(
                TEST_DIR.parent
                / "Bin"
                / SYSTEM
                / ("fastgmad.exe" if SYSTEM == "Windows" else "fastgmad")
            ),
        }

        with self.assertRaises(RuntimeError) as ctx:
            extract_addons.run_addon_extraction(exec_paths)

        self.assertIn("Cannot write to the current folder", str(ctx.exception))

    def test_worker_count_stays_conservative(self):
        self.assertEqual(extraction_workers(16, cores=1), 1)
        self.assertEqual(extraction_workers(16, cores=2), 1)
        self.assertEqual(extraction_workers(16, cores=3), 1)
        self.assertEqual(extraction_workers(16, cores=4), 2)
        self.assertEqual(extraction_workers(16, cores=8), 6)
        self.assertEqual(extraction_workers(10, cores=128), 10)
        self.assertEqual(extraction_workers(16, cores=128), 16)

        prev = 0
        for cores in range(1, 129):
            threads = extraction_workers(16, cores=cores)
            self.assertGreaterEqual(threads, 1)
            self.assertLessEqual(threads, 16)
            self.assertLessEqual(threads, max(1, cores - 2))
            self.assertGreaterEqual(threads, prev)
            prev = threads


class SystemInfoTests(unittest.TestCase):
    def test_join_parts_drops_empty_parts(self):
        self.assertEqual(join_parts("a", None, "", "b"), "a b")

    def test_system_info_is_clean_single_line(self):
        info = get_system_info()
        self.assertTrue(info)
        self.assertNotIn("  ", info)
        self.assertNotIn(chr(10), info)


class VersionIdentityTests(unittest.TestCase):
    def test_app_version_names_a_real_build(self):
        self.assertRegex(app_version, r"^v2\.9\.0 \((?:[0-9a-f]{7}|dev|release)\)$")

    def test_build_date_starts_with_a_date(self):
        self.assertRegex(build_date, r"^\d{4}-\d{2}-\d{2} \(")


if __name__ == "__main__":
    unittest.main()
