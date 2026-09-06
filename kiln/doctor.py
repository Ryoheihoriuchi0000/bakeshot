"""焼く前に足りないものを調べる。**時間を使う前に**気づけるように。"""
import platform
import shutil
import subprocess
from pathlib import Path


def _run(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, str(e)


def checks(root: Path = None):
    """(見出し, 通ったか, 直し方) の一覧。"""
    out = []

    ok = platform.machine() == "arm64"
    out.append(("Apple silicon の Mac", ok,
                "Intel Mac では動きません（iOS アプリを Mac で動かせないため）"))

    code, sel = _run(["/usr/bin/xcode-select", "-p"])
    ok = code == 0 and "CommandLineTools" not in sel
    out.append(("Xcode", ok,
                "Xcode が要ります。入れてから `sudo xcode-select -s /Applications/Xcode.app` を実行してください"))

    ok = shutil.which("ruby") is not None
    out.append(("Ruby", ok, "macOS 標準の ruby が見つかりません"))

    code, _ = _run(["/usr/bin/env", "ruby", "-e", "require 'xcodeproj'"])
    out.append(("xcodeproj gem", code == 0,
                "`gem install --user-install xcodeproj` を実行してください"))

    if root:
        projs = [p for p in Path(root).glob("*.xcodeproj") if not p.name.endswith("-Kiln.xcodeproj")]
        out.append((".xcodeproj", bool(projs),
                    f"{root} に .xcodeproj がありません。プロジェクトの根で実行してください"))
    return out


def report(root: Path = None, quiet_when_ok: bool = False) -> bool:
    rows = checks(root)
    bad = [r for r in rows if not r[1]]
    if not (bad or not quiet_when_ok):
        return True
    for name, ok, fix in rows:
        print(f"  {'✓' if ok else '✗'} {name}" + ("" if ok else f"  → {fix}"))
    if bad:
        print("\n足りないものがあります。上の指示に従ってから、もう一度実行してください。")
    else:
        print("\n準備できています。`kiln init` から始めてください。")
        print("※ 初めて焼く時に「Kiln が Xcode を制御することを許可しますか」と聞かれます。許可してください。")
    return not bad
