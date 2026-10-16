import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

CORE_DIR = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import ui
from rich.console import Console
from rich.text import Text


class NoColorTests(unittest.TestCase):
    def test_no_color_env_strips_ansi_colors(self):
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            console = Console(file=io.StringIO(), force_terminal=True, theme=ui.THEME)
            console.print(Text("plain text", style="red"))

        out = console.file.getvalue()
        self.assertIn("plain text", out)
        self.assertNotIn("\x1b[", out)

    def test_without_no_color_ansi_colors_stay(self):
        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}

        with mock.patch.dict(os.environ, env, clear=True):
            console = Console(file=io.StringIO(), force_terminal=True, theme=ui.THEME)
            console.print(Text("plain text", style="red"))

        self.assertIn("\x1b[", console.file.getvalue())

    def test_app_console_respects_no_color(self):
        self.assertIs(ui.console.no_color, os.environ.get("NO_COLOR", "") != "")


if __name__ == "__main__":
    unittest.main()
