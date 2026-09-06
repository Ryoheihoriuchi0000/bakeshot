"""焼く本体。本物の iOS ランタイム（My Mac / Designed for iPad）でアプリの View を描く。

⚠ `xcodebuild test` はホストの起動で死ぬ（Xcode 26.3、最小アプリでも再現）。
  同じ xcodeproj を Xcode IDE が走らせると通るので、AppleScript で Xcode を操作する。
"""
import re
import shutil
import time
import uuid
from pathlib import Path

from . import devices, scenes as scenes_mod, xcode

KIT = Path(__file__).parent / "hostkit"
CONTAINERS = Path.home() / "Library" / "Containers"


def log(msg, kind="·"):
    print(f"{kind} {msg}", flush=True)


def find_out_dir(token: str):
    """アプリのサンドボックスにある受け皿。コンテナは走るまで決まらない。"""
    for c in CONTAINERS.iterdir() if CONTAINERS.is_dir() else []:
        d = c / "Data" / "tmp" / "kiln_out" / token
        if d.is_dir():
            return d
    return None


def ensure_scenes(root: Path, module: str, imports: str) -> Path:
    """台本を用意する。**何をどんな状態で撮るかは利用者（とそのエージェント）が書く。**
    自動検出は下書きでしかない（空の初期状態しか出せない）。"""
    d = root / "Kiln"
    f = d / "Scenes.swift"
    if f.exists():
        return f
    d.mkdir(parents=True, exist_ok=True)
    views = scenes_mod.guess_views(root)
    f.write_text(scenes_mod.draft(module, imports, views), encoding="utf-8")
    guide = KIT / "scenes_guide.md"
    if guide.exists():
        (d / "台本の書き方.md").write_text(
            guide.read_text(encoding="utf-8").replace("__MODULE__", module), encoding="utf-8")
    log(f"Kiln/Scenes.swift に下書きを置きました（{len(views)} 画面）。"
        f"何をどんな状態で撮るかは、ここを直してください", "!")
    return f


def bake(root: Path, project: Path, app_target: str, locale: str, device: str,
         out_root: Path, bundle_id: str = "", strip_ext: bool = True,
         strip_ent: bool = False, team: str = "", keep: bool = False):
    module = app_target.replace("-", "_")
    imports = "".join(f"#if canImport({m})\nimport {m}\n#endif\n"
                      for m in sorted(scenes_mod.local_package_modules(root)))
    scenes_file = ensure_scenes(root, module, imports)
    names = scenes_mod.names(scenes_file.read_text(encoding="utf-8"))
    if not names:
        raise SystemExit("台本に絵がありません。Kiln/Scenes.swift に shot / shotBoth を書いてください。")

    token = uuid.uuid4().hex[:8]
    work = root / "Kiln" / ".work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    w, h, top, bottom, _px = devices.metrics(device)
    test = (KIT / "RenderTests.swift.template").read_text(encoding="utf-8")
    for k, v in [("__IMPORTS__", imports), ("__MODULE__", module), ("__TOKEN__", token),
                 ("__W__", str(w)), ("__H__", str(h)), ("__TOP__", str(top)), ("__BOTTOM__", str(bottom))]:
        test = test.replace(k, v)
    test_file = work / "RenderTests.swift"
    test_file.write_text(test, encoding="utf-8")
    api_file = work / "KilnSceneAPI.swift"
    api_file.write_text((KIT / "KilnSceneAPI.swift.template").read_text(encoding="utf-8"), encoding="utf-8")

    log(f"台本にある {len(names)} 枚を焼きます（{locale} / {device}\"）")

    # 1) xcodeproj を複製してテストターゲットを足す
    dst = project.with_name(project.stem + "-Kiln.xcodeproj")
    xcode.close_project(dst)
    code, out = xcode.run(["/usr/bin/env", "ruby", str(KIT / "add_test_target.rb"),
                           str(project), str(dst),
                           ":".join([str(test_file), str(api_file), str(scenes_file)]),
                           app_target, bundle_id, "1" if strip_ext else "0",
                           "1" if strip_ent else "0", locale, team,
                           str(work / "widget")], env_extra=xcode.UTF8)
    if code != 0:
        if "cannot load such file -- xcodeproj" in out:
            raise SystemExit("Ruby の xcodeproj gem がありません。`gem install --user-install xcodeproj` を実行してください")
        raise SystemExit(f"xcodeproj の複製に失敗:\n{out[-800:]}")

    # 2) 先にビルドだけ通す（Xcode 経由だとコンパイルエラーが読めない）。
    #    引数が要る View が台本に混ざっていたら、その行を外して組み直す
    dest_id = xcode.mac_destination_id(dst)
    derived = work / "dd"
    pruned = []
    for attempt in range(1, 5):
        code, out = xcode.build_for_testing(dst, dest_id, derived)
        if code == 0:
            break
        errs = [l for l in out.splitlines() if ": error:" in l]
        bad = {int(m.group(1)) for l in errs
               for m in [re.search(r"RenderTests\.swift:(\d+):", l)] if m}
        if not bad or attempt == 4:
            why = " / ".join(re.sub(r"^.*?: error: ", "", l) for l in errs[:4])
            raise SystemExit(f"ビルドに失敗しました:\n{why or out[-600:]}")
        lines = test_file.read_text(encoding="utf-8").splitlines()
        for n in sorted(bad, reverse=True):
            if n - 1 < len(lines):
                m = re.search(r'bake\("([^"]+?)(?:_light|_dark)?"', lines[n - 1])
                if m and m.group(1) not in pruned:
                    pruned.append(m.group(1))
                lines[n - 1] = ""
        test_file.write_text("\n".join(lines), encoding="utf-8")
        log(f"引数が要るので外しました: {', '.join(pruned)}", "!")

    # 3) Xcode に走らせ、進捗ファイルで打ち切る。
    #    落ちる View があるとテストの完了が返ってこないので、Xcode の完了は当てにしない。
    out_dir_final = out_root / locale
    out_dir_final.mkdir(parents=True, exist_ok=True)
    remaining = [n for n in names if n not in pruned]
    failed, collected, rounds = [], 0, 0
    start_s = str(KIT / "start_test.applescript")
    stop_s = str(KIT / "stop_test.applescript")
    try:
        while remaining and rounds < len(names) + 2:
            rounds += 1
            log("Xcode で My Mac (Designed for iPad) を実行しています…" if rounds == 1
                else f"残り {len(remaining)} 枚でもう一周（{rounds} 回目）")
            box = find_out_dir(token)
            if box:
                for f in ("STATE", "LOG"):
                    (box / f).unlink(missing_ok=True)
                # 落ちた絵は飛ばす。ソースではなくこのファイルで伝える（再ビルドを起こさない）
                (box / "SKIP").write_text("\n".join(failed + pruned), encoding="utf-8")
            code, out = xcode.osascript([start_s, str(dst), "KilnRender"])
            if "not loaded" in out:
                raise SystemExit("Xcode がプロジェクトを開けませんでした")

            last, last_change, finished = "", time.time(), False
            deadline = time.time() + (1200 if rounds == 1 else 600)
            while time.time() < deadline:
                time.sleep(1)
                box = box or find_out_dir(token)
                if not box:
                    continue
                now = (box / "STATE").read_text(encoding="utf-8") if (box / "STATE").exists() else ""
                if now != last:
                    last, last_change = now, time.time()
                if now.startswith("FINISHED"):
                    finished = True
                    break
                if last and time.time() - last_change > 30:
                    break
            xcode.osascript([stop_s, str(dst)])
            if not box:
                raise SystemExit("Xcode でテストが始まりませんでした（ビルドが通っていない可能性）")

            done = set()
            for f in sorted(box.glob("*.png")):
                shutil.copy2(f, out_dir_final / f.name)
                f.unlink()
                collected += 1
                done.add(f.stem)
            fresh = [n for n in remaining if n in done]
            for n in fresh:
                log(f"✓ {n}", "")
            remaining = [n for n in remaining if n not in done]
            if finished:
                break

            parts = last.strip().split(" ")
            if len(parts) == 2 and parts[0] in ("STARTED", "TIMEOUT") and parts[1] in remaining:
                remaining.remove(parts[1])
                failed.append(parts[1])
                log(f"✗ {parts[1]} は焼いている最中に"
                    f"{'固まった' if parts[0] == 'TIMEOUT' else '落ちた'}ので外しました", "!")
            elif not last and not done:
                raise SystemExit(f"Xcode でテストが動きませんでした（{rounds} 回目）")
            elif not fresh:
                tail = ""
                if (box / "LOG").exists():
                    tail = " / ".join(box.read_text if False else
                                      (box / "LOG").read_text(encoding="utf-8").splitlines()[-4:])
                log(f"これ以上進みません。残り {len(remaining)} 枚は焼けませんでした（最後の様子: {tail or '記録なし'}）", "!")
                failed += remaining
                remaining = []
    finally:
        xcode.osascript([stop_s, str(dst), "close"])
        if not keep:
            shutil.rmtree(dst, ignore_errors=True)

    log(f"{collected} 枚できました → {out_dir_final}", "✓")
    if failed or pruned:
        log(f"焼けなかった: {', '.join(sorted(set(failed + pruned)))}", "!")
    return collected
