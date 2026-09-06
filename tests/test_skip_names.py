"""落ちた画面を飛ばす名前の作り方。
ここがずれていると、落ちた画面を毎周やり直して永遠に終わらない（実際そうなっていた）。"""
import re
import unittest


def skip_list(failed, pruned):
    """bake.py が SKIP に書くもの。撮影側は _light/_dark を落とした名前で照合する。"""
    return sorted({re.sub(r"_(light|dark)$", "", n) for n in failed + pruned})


class SkipNames(unittest.TestCase):
    def test_suffix_is_stripped(self):
        self.assertEqual(skip_list(["ExploreTab_light"], []), ["ExploreTab"])

    def test_light_and_dark_collapse_to_one_entry(self):
        self.assertEqual(skip_list(["Home_light", "Home_dark"], []), ["Home"])

    def test_names_without_a_suffix_survive(self):
        self.assertEqual(skip_list(["paywall"], []), ["paywall"])

    def test_only_the_trailing_suffix_goes(self):
        self.assertEqual(skip_list(["dark_mode_light"], []), ["dark_mode"])

    def test_pruned_scenes_are_included(self):
        self.assertEqual(skip_list(["A_light"], ["B_dark"]), ["A", "B"])


class CrashReason(unittest.TestCase):
    """落ちた理由の拾い方。ノイズを外して fatalError の行だけ返す。"""

    def _box(self, text):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        (d / "STDERR").write_text(text, encoding="utf-8")
        return d

    def test_picks_the_fatal_error_line(self):
        from bakeshot.bake import crash_reason
        box = self._box(
            "objc[123]: chatter\n"
            "SwiftUI/EnvironmentObject.swift:1: Fatal error: No ObservableObject of type Client found.\n"
            "A View.environmentObject(_:) for Client may be missing.\n")
        why = crash_reason(box)
        self.assertIn("No ObservableObject of type Client", why)
        self.assertNotIn("objc[", why)

    def test_no_file_means_no_reason(self):
        import tempfile
        from pathlib import Path
        from bakeshot.bake import crash_reason
        self.assertEqual(crash_reason(Path(tempfile.mkdtemp())), "")

    def test_falls_back_to_the_last_useful_line(self):
        from bakeshot.bake import crash_reason
        self.assertEqual(crash_reason(self._box("nw_connection noise\nsomething went wrong\n")),
                         "something went wrong")
