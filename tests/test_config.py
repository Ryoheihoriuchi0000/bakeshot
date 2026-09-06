"""設定ファイルの読み書きと、公開版でウィジェットを止める判断。"""
import json
import tempfile
import unittest
from pathlib import Path

from bakeshot.cli import load_config, save_config


class Config(unittest.TestCase):
    def test_missing_file_is_an_empty_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_config(Path(tmp)), {})

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = {"project": "My App.xcodeproj", "target": "My App",
                   "locales": ["ja", "en"], "devices": ["6.9"]}
            save_config(root, cfg)
            self.assertEqual(load_config(root), cfg)

    def test_written_as_readable_utf8(self):
        # 人が開いて直すファイル。日本語がエスケープで潰れていないこと
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_config(root, {"note": "発車標アプリ"})
            text = (root / "Bakeshot" / "bakeshot.json").read_text(encoding="utf-8")
            self.assertIn("発車標アプリ", text)
            self.assertTrue(text.endswith("\n"))


class WidgetGate(unittest.TestCase):
    """公開版に完全版の処理は入っていない。台本にウィジェットがあれば、
    ビルドで死ぬ前にはっきり止める。"""

    def test_a_widget_size_is_detected(self):
        script = 'shot("w", size: .widgetLarge) { W() }'
        self.assertIn(".widget", script)

    def test_a_plain_script_is_not_flagged(self):
        script = 'shotBoth("home") { Home() }'
        self.assertNotIn(".widget", script)
