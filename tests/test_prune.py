"""ビルドが通らないときの外し方。
撮影行以外を消すと土台が壊れて、無関係な構文エラーで本当の原因が埋まる。"""
import unittest
from bakeshot.bake import error_lines, failing_shot_lines, skip_names

SCRIPT = [
    "import SwiftUI",                                   # 1
    "enum BakeshotScenes {",                            # 2
    '    bake("home_light", dark: false) { Home() }',   # 3
    '    bake("paywall", dark: true) { Paywall(x: 1) }',# 4
    "}",                                                # 5
]


def err(line, msg="cannot find 'Paywall' in scope"):
    return f"/x/RenderTests.swift:{line}:9: error: {msg}"


class ErrorLines(unittest.TestCase):
    def test_only_error_lines(self):
        out = "note: something\n" + err(4) + "\nwarning: unused\n"
        self.assertEqual(error_lines(out), [err(4)])


class FailingShotLines(unittest.TestCase):
    def test_finds_the_shot_that_failed(self):
        self.assertEqual(failing_shot_lines([err(4)], SCRIPT), [(4, "paywall")])

    def test_strips_the_light_dark_suffix_from_the_name(self):
        self.assertEqual(failing_shot_lines([err(3)], SCRIPT), [(3, "home")])

    def test_errors_outside_a_shot_line_are_never_touched(self):
        # 土台の行（import / enum / 閉じ括弧）は消してはいけない
        for line in (1, 2, 5):
            self.assertEqual(failing_shot_lines([err(line)], SCRIPT), [], f"line {line}")

    def test_line_numbers_past_the_file_are_ignored(self):
        self.assertEqual(failing_shot_lines([err(99)], SCRIPT), [])

    def test_errors_without_a_render_tests_line_are_ignored(self):
        self.assertEqual(failing_shot_lines(["/x/Other.swift:4:1: error: boom"], SCRIPT), [])

    def test_reports_bottom_up_so_deleting_does_not_shift_lines(self):
        hits = failing_shot_lines([err(3), err(4)], SCRIPT)
        self.assertEqual([n for n, _ in hits], [4, 3])


class SkipNames(unittest.TestCase):
    def test_light_and_dark_collapse(self):
        self.assertEqual(skip_names(["Home_light", "Home_dark", "paywall"]), ["Home", "paywall"])
