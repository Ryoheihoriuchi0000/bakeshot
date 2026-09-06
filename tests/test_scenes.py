"""台本まわり。Xcode が無くても回るところだけを見る。"""
import unittest
from pathlib import Path
import tempfile

from bakeshot import scenes


class ModuleName(unittest.TestCase):
    def test_spaces_and_dashes_become_underscores(self):
        # Xcode の既定のモジュール名に合わせる。"Food Truck" は Food_Truck
        self.assertEqual(scenes.module_name("Food Truck"), "Food_Truck")
        self.assertEqual(scenes.module_name("My-App"), "My_App")
        self.assertEqual(scenes.module_name("Tally"), "Tally")

    def test_leading_digit_gets_a_prefix(self):
        self.assertEqual(scenes.module_name("1Password"), "_1Password")


class LocalPackages(unittest.TestCase):
    def _pkg(self, root: Path, name: str, body: str):
        d = root / name
        (d / "Sources" / "Inner").mkdir(parents=True)
        (d / "Package.swift").write_text(body, encoding="utf-8")

    def test_reads_target_names_not_folder_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._pkg(root, "Kit", '''
                let package = Package(
                    name: "Kit",
                    targets: [.target(name: "Kit", path: "Sources")]
                )
            ''')
            # Sources/ の中は区分であってモジュールではない。Inner を拾ったら誤り
            self.assertEqual(scenes.local_package_modules(root), {"Kit"})

    def test_skips_names_that_are_not_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._pkg(root, "Gen", 'targets: [.target(name: "Fine")]')
            (root / "Gen" / "Sources" / "protoc-gen-swift").mkdir()
            mods = scenes.local_package_modules(root)
            self.assertIn("Fine", mods)
            self.assertNotIn("protoc-gen-swift", mods)

    def test_ignores_build_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._pkg(root, ".build", 'targets: [.target(name: "Vendored")]')
            self.assertEqual(scenes.local_package_modules(root), set())


class SceneNames(unittest.TestCase):
    def test_picks_up_both_forms(self):
        text = '''
            shotBoth("home") { HomeView() },
            [shot("paywall", dark: true) { Paywall() }],
        '''
        # shotBoth は明暗2枚、shot は1枚。名前がそのまま出力ファイル名になる
        self.assertEqual(scenes.names(text), ["home_light", "home_dark", "paywall"])

    def test_empty_script_has_no_names(self):
        self.assertEqual(scenes.names("// nothing here"), [])


if __name__ == "__main__":
    unittest.main()
