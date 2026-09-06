"""撮影台本（Bakeshot/Scenes.swift）の読み書き。"""
import re
from pathlib import Path

SHOT_RE = re.compile(r'\b(shot|shotBoth)\s*\(\s*"([^"]+)"')
# 引数なしで作れそうな View。下書きを作るためだけの雑な当たり
VIEW_RE = re.compile(r"(?m)^(?:public |internal )?struct\s+(\w+)\s*:\s*(?:[^{]*\b)?View\b[^{]*\{")


def names(text: str):
    """台本に並んでいる絵の名前。落ちた絵を外すのに使う。"""
    out = []
    for kind, name in SHOT_RE.findall(text):
        for n in ([f"{name}_light", f"{name}_dark"] if kind == "shotBoth" else [name]):
            if n not in out:
                out.append(n)
    return out


def guess_views(root: Path, limit: int = 8):
    """下書き用。引数なしで作れそうな View を雑に拾う。
    **当たりを付けるだけ**で、正しさは求めない（台本は人とエージェントが直す）。"""
    found = []
    skip_dirs = {".git", "DerivedData", "build", ".build", "Pods", "Carthage", "Bakeshot"}
    for p in sorted(root.rglob("*.swift")):
        if any(part in skip_dirs or part.endswith(".xcodeproj") for part in p.parts):
            continue
        low = str(p).lower()
        if "watch" in low or "/test" in low or "tests/" in low:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "import WatchKit" in text:
            continue
        for m in VIEW_RE.finditer(text):
            name = m.group(1)
            body = text[m.end():m.end() + 1500]
            # 既定値の無い stored property / @Binding があると `View()` では作れない
            bad = re.search(r"(?m)^\s*(?:@Binding|@ObservedObject|@EnvironmentObject)\b", body) \
                or re.search(r"(?m)^\s*(?:let|var)\s+\w+\s*:\s*[^={\n]+$", body) \
                or re.search(r"(?m)^\s*@State\s+(?:public |private )?var\s+\w+\s*:\s*[^={\n]+$", body)
            if bad:
                continue
            if name not in found:
                found.append(name)
            if len(found) >= limit:
                return found
    return found


_TARGET = re.compile(r"\.(?:target|executableTarget|binaryTarget)\(\s*name:\s*\"([A-Za-z_][A-Za-z0-9_]*)\"")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def module_name(target: str) -> str:
    """Xcode の既定のモジュール名。識別子に使えない字は _ に置き換わる（"Food Truck" → Food_Truck）。"""
    name = re.sub(r"[^A-Za-z0-9_]", "_", target)
    return "_" + name if name[:1].isdigit() else name


def local_package_modules(root: Path):
    """ローカル SPM パッケージのモジュール名。
    アプリのモジュールを import しただけでは、そこの型（Theme / RouterPath 等）が見えない。

    Package.swift のターゲット名を読む。Sources/ 直下のフォルダ名を拾うと、
    モジュールではなく中の区分（Model / Assets.xcassets 等）まで import してしまう。"""
    out = set()
    for pkg in root.rglob("Package.swift"):
        if any(part in {".git", "DerivedData", ".build", "build"} for part in pkg.parts):
            continue
        try:
            text = pkg.read_text(encoding="utf-8")
        except Exception:
            continue
        names = set(_TARGET.findall(text))
        if names:
            out |= names
            continue
        src = pkg.parent / "Sources"     # 読めなかったときだけ、フォルダ名で当てる
        if src.is_dir():
            for m in src.iterdir():
                if m.is_dir() and not m.name.startswith("."):
                    out.add(m.name)
    return {m for m in out if _IDENT.match(m)}


def draft(module: str, imports: str, views):
    lines = "".join(f'            shotBoth("{v}") {{ {v}() }},\n' for v in views)
    if not lines:
        lines = "            // 引数なしで作れる View が見つかりませんでした。手で足してください。\n"
    return f'''// Bakeshot の撮影台本。**ここを直してください。**
//
// 下は自動で作った下書きで、どの画面も「初期状態（データなし）」で焼きます。
// 売り物の絵にするには、見せたい状態を自分で作って渡します。書き方は 台本の書き方.md へ。
import SwiftUI
{imports}@testable import {module}

enum BakeshotScenes {{
    @MainActor static var scenes: [BakeshotScene] {{
        [
{lines}        ].flatMap {{ $0 }}
    }}
}}
'''
