import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "bakeshot" / "hostkit"


class MultiLocale(unittest.TestCase):
    def test_render_template_loops_locales(self):
        s = (KIT / "RenderTests.swift.template").read_text(encoding="utf-8")
        self.assertIn("for loc in __LOCALES__", s)
        self.assertIn("BakeshotRuntime.shared.locale = loc", s)
        # 言語ごとのフォルダに書く
        self.assertIn('dir.appendingPathComponent("\\(name).png")', s)

    def test_scene_api_has_runtime_box(self):
        s = (KIT / "BakeshotSceneAPI.swift.template").read_text(encoding="utf-8")
        self.assertIn("public final class BakeshotRuntime", s)
        self.assertIn("BakeshotRuntime.shared.locale", s)

    def test_swift_literal(self):
        # bake() が作る Swift の配列リテラルと同じ組み立て
        for locales, want in ([["ja"], '["ja"]'], [["ja", "en"], '["ja", "en"]'],
                              [['zh"x'], '["zhx"]']):
            got = "[" + ", ".join('"%s"' % l.replace('"', '') for l in locales) + "]"
            self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
