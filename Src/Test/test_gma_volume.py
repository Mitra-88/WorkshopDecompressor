import lzma
import os
import platform
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from time import perf_counter

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import extract_addons

TEST_DIR = Path(__file__).resolve().parent
SYSTEM = platform.system()
BIN_DIR = TEST_DIR.parent.parent / "Src" / "Bin" / SYSTEM
EXE_SUFFIX = ".exe" if SYSTEM == "Windows" else ""

TOTAL_GMAS = 60
TOTAL_BINS = 15
MIN_SIZE = 400 * 1024
MAX_SIZE = 60 * 1024 * 1024
SEED = 20260924
WRITE_CHUNK = 1024 * 1024
DIST_MODE = (
    "--dist" in sys.argv or os.environ.get("WD_VOLUME_TARGET", "").lower() == "dist"
)
GENERATE_ONLY = "--generate-only" in sys.argv
REPO_ROOT = TEST_DIR.parent.parent


def build_gma(entry_name, entry_size):
    header = bytearray()
    header += b"GMAD"
    header += bytes([3])
    header += (0).to_bytes(8, "little")
    header += (0).to_bytes(8, "little")
    header += b"\x00"
    header += b"Volume Test Addon\x00"
    header += b"{}\x00"
    header += b"tester\x00"
    header += (1).to_bytes(4, "little")
    header += (1).to_bytes(4, "little")
    header += entry_name.encode() + b"\x00"
    header += entry_size.to_bytes(8, "little")
    header += (0).to_bytes(4, "little")
    header += (0).to_bytes(4, "little")
    return bytes(header)


def write_gma(path, entry_name, entry_size, rng):
    with open(path, "wb") as f:
        f.write(build_gma(entry_name, entry_size))
        f.write(os.urandom(min(entry_size, 64 * 1024)))
        remaining = entry_size - min(entry_size, 64 * 1024)
        chunk = b"\x00" * WRITE_CHUNK
        while remaining > 0:
            block = chunk[: min(remaining, WRITE_CHUNK)]
            f.write(block)
            remaining -= len(block)


class GmaVolumeTests(unittest.TestCase):
    def test_volume_roundtrip_gmas_and_bins(self):
        if DIST_MODE or GENERATE_ONLY:
            tmp = REPO_ROOT / "dist" / "volume"
            keep = True
        else:
            tmp = Path(tempfile.mkdtemp(prefix="wd-gma-volume-"))
            keep = False

        old_cwd = os.getcwd()

        tmp.mkdir(parents=True, exist_ok=True)
        os.chdir(tmp)
        self.addCleanup(os.chdir, old_cwd)
        self.addCleanup(
            lambda: None if keep else shutil.rmtree(tmp, ignore_errors=True)
        )

        rng = random.Random(SEED)
        total_bytes = 0
        expected_sizes = {}

        start = perf_counter()
        for index in range(TOTAL_GMAS):
            unit = rng.random() ** 4
            entry_size = int(MIN_SIZE + (MAX_SIZE - MIN_SIZE) * unit)
            gma_path = tmp / f"volume_{index:03d}.gma"
            write_gma(gma_path, f"build/data_{index}.bin", entry_size, rng)
            total_bytes += gma_path.stat().st_size
            expected_sizes[f"data_{index}.bin"] = entry_size

        for index in range(TOTAL_BINS):
            unit = rng.random() ** 4
            inner_size = int(MIN_SIZE + (MAX_SIZE - MIN_SIZE) * unit)
            inner_gma = (
                build_gma(f"build/legacy_{index}.bin", inner_size)
                + b"\x00" * inner_size
            )
            bin_path = tmp / f"legacy_{index:03d}.bin"
            bin_path.write_bytes(
                lzma.compress(inner_gma, format=lzma.FORMAT_ALONE, preset=1)
                + b"WD-TRAILING-DATA"
            )
            total_bytes += bin_path.stat().st_size
            expected_sizes[f"legacy_{index}.bin"] = inner_size

        if GENERATE_ONLY:
            copy_app_bundle(tmp)
            print(
                f"\ngenerated {TOTAL_GMAS} .gma + {TOTAL_BINS} .bin "
                f"({total_bytes / (1024 * 1024):.1f} MiB) in {tmp}"
            )
            print("copy or point the program at this folder and choose Extract Addons.")
            return

        exec_paths = {
            "7z": str(BIN_DIR / f"7z{EXE_SUFFIX}"),
            "fastgmad": str(BIN_DIR / f"fastgmad{EXE_SUFFIX}"),
        }
        summary = extract_addons.run_addon_extraction(exec_paths)

        self.assertEqual(summary["gma_found"], TOTAL_GMAS + TOTAL_BINS)
        self.assertEqual(summary["bin_found"], TOTAL_BINS)
        self.assertEqual(summary["gma_processed"], TOTAL_GMAS + TOTAL_BINS)
        self.assertEqual(summary["bin_processed"], TOTAL_BINS)
        self.assertEqual(summary["failures"], [])
        self.assertEqual(len(summary["warnings"]), TOTAL_BINS)
        self.assertEqual(summary["moved"], TOTAL_GMAS + TOTAL_BINS * 2)

        addon_dirs = list((tmp / "Extracted-Addons").glob("Addon*"))
        self.assertEqual(len(addon_dirs), TOTAL_GMAS + TOTAL_BINS)

        extracted_sizes = {
            p.name: p.stat().st_size
            for p in (tmp / "Extracted-Addons").glob("Addon*/build/*.bin")
        }
        self.assertEqual(extracted_sizes, expected_sizes)

        leftover_gmas = list((tmp / "Leftover").glob("*.gma"))
        self.assertEqual(len(leftover_gmas), TOTAL_GMAS + TOTAL_BINS)
        leftover_bins = list((tmp / "Leftover").glob("*.bin"))
        self.assertEqual(len(leftover_bins), TOTAL_BINS)

        elapsed = perf_counter() - start
        print(
            f"\nvolume roundtrip: {TOTAL_GMAS} .gma + {TOTAL_BINS} .bin, "
            f"{total_bytes / (1024 * 1024):.1f} MiB of generated files in {elapsed:.1f}s"
        )
        if keep:
            print(f"files left in place for inspection: {tmp}")


def copy_app_bundle(target):
    exe = next(REPO_ROOT.glob("dist/WorkshopDecompressor*"), None)
    if exe is None:
        print("packaged program not found in dist, copy it there manually to test.")
        return
    shutil.copy2(exe, target / exe.name)
    bin_src = REPO_ROOT / "dist" / "Bin"
    if bin_src.is_dir():
        shutil.copytree(bin_src, target / "Bin", dirs_exist_ok=True)
    print("copied the packaged program and Bin folder next to the generated files.")


if __name__ == "__main__":
    unittest.main(
        argv=[sys.argv[0]]
        + [a for a in sys.argv[1:] if a not in ("--dist", "--generate-only")]
    )
