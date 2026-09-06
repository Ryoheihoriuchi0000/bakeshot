"""Xcode まわりの外部コマンド。ここに閉じ込めておく。"""
import re
import subprocess
from pathlib import Path

UTF8 = {"LC_ALL": "en_US.UTF-8", "LANG": "en_US.UTF-8"}


def run(args, env_extra=None, timeout=None):
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def osascript(args):
    return run(["/usr/bin/osascript"] + args)


def xcode_is_running() -> bool:
    code, _ = run(["/usr/bin/pgrep", "-x", "Xcode"])
    return code == 0


def close_project(path: Path):
    """開いたまま作り直すと「別のアプリが変更」ダイアログで止まる。
    ⚠ `tell application "Xcode"` は起動していなければ **起動してしまう** ので、先に確かめる。"""
    if not xcode_is_running():
        return
    # path は Xcode 側の表記と食い違うことがある（/tmp と /private/tmp）。名前でも閉じる
    name = path.name
    osascript(["-e",
               f'tell application "Xcode" to close (every workspace document whose path is "{path}") saving no'])
    osascript(["-e",
               f'tell application "Xcode" to close (every workspace document whose name is "{name}") saving no'])


def mac_destination_id(project: Path, scheme: str = "BakeshotRender") -> str:
    """「My Mac (Designed for iPad)」の宛先 id。
    `variant=Designed for [iPad,iPhone]` はカンマで xcodebuild のパーサが落ちるので id で渡す。"""
    _, out = run(["/usr/bin/xcrun", "xcodebuild", "-showdestinations",
                  "-project", str(project), "-scheme", scheme])
    for line in out.splitlines():
        if "platform:macOS" in line and "Designed for" in line:
            m = re.search(r"id:([0-9A-Fa-f-]+)", line)
            if m:
                return m.group(1)
    raise SystemExit(
        "My Mac (Designed for iPad) の宛先が見つかりません。\n"
        "Apple silicon の Mac と、iOS を対象にしたアプリのターゲットが要ります。")


def build_for_testing(project: Path, dest_id: str, derived: Path, scheme: str = "BakeshotRender"):
    return run(["/usr/bin/xcrun", "xcodebuild", "build-for-testing",
                "-project", str(project), "-scheme", scheme,
                "-destination", f"platform=macOS,arch=arm64,id={dest_id}",
                "-derivedDataPath", str(derived),
                "-allowProvisioningUpdates", "-quiet"])
