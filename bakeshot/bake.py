"""焼く本体。本物の iOS ランタイム（My Mac / Designed for iPad）でアプリの View を描く。

⚠ `xcodebuild test` はホストの起動で死ぬ（Xcode 26.3、最小アプリでも再現）。
  同じ xcodeproj を Xcode IDE が走らせると通るので、AppleScript で Xcode を操作する。
"""
import re
import shutil
import time
import uuid
from pathlib import Path

from . import devices, features, scenes as scenes_mod, xcode

KIT = Path(__file__).parent / "hostkit"
CONTAINERS = Path.home() / "Library" / "Containers"


def log(msg, kind="·"):
    print(f"{kind} {msg}", flush=True)


_used_widgets = False


def used_widgets() -> bool:
    return _used_widgets


def error_lines(out: str):
    """ビルド出力からコンパイルエラーの行だけ。"""
    return [l for l in out.splitlines() if ": error:" in l]


def failing_shot_lines(errs, lines):
    """エラーの出た行のうち、**撮影行だけ**を返す。

    撮影行以外を消すと土台のコードが壊れ、無関係な構文エラーだらけになって
    本当の原因が見えなくなる。実際にそうなっていたので、ここは厳しくする。
    戻り値は [(行番号1始まり, 画面の名前)]。"""
    nums = {int(m.group(1)) for l in errs
            for m in [re.search(r"RenderTests\.swift:(\d+):", l)] if m}
    found = []
    for n in sorted(nums, reverse=True):
        if n - 1 >= len(lines):
            continue
        m = re.search(r'bake\("([^"]+?)(?:_light|_dark)?"', lines[n - 1])
        if m:
            found.append((n, m.group(1)))
    return found


def skip_names(names):
    """撮影側は _light / _dark を落とした名前で照合する。合わせないと素通りする。"""
    return sorted({re.sub(r"_(light|dark)$", "", n) for n in names})


# fatalError などのメッセージは stderr に出てからプロセスが死ぬ。描画側がそれをファイルに残す
_NOISE = ("<unknown>", "CoreSimulator", "nw_", "objc[", "Metal", "AVF ", "Could not create")


def crash_reason(box) -> str:
    """落ちた理由を1〜2行で。何も無ければ空。"""
    if not box:
        return ""
    f = box / "STDERR"
    if not f.exists():
        return ""
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    keep = [l for l in lines if not any(n in l for n in _NOISE)]
    fatal = [i for i, l in enumerate(keep) if "Fatal error" in l or "Precondition failed" in l]
    if fatal:
        i = fatal[-1]
        return " ".join(keep[i:i + 2])[:300]
    return keep[-1][:300] if keep else ""


def find_out_dir(token: str):
    """アプリのサンドボックスにある受け皿。コンテナは走るまで決まらない。"""
    for c in CONTAINERS.iterdir() if CONTAINERS.is_dir() else []:
        d = c / "Data" / "tmp" / "bakeshot_out" / token
        if d.is_dir():
            return d
    return None


def ensure_scenes(root: Path, module: str, imports: str) -> Path:
    """台本を用意する。**何をどんな状態で撮るかは利用者（とそのエージェント）が書く。**
    自動検出は下書きでしかない（空の初期状態しか出せない）。"""
    d = root / "Bakeshot"
    f = d / "Scenes.swift"
    if f.exists():
        return f
    d.mkdir(parents=True, exist_ok=True)
    views = scenes_mod.guess_views(root)
    f.write_text(scenes_mod.draft(module, imports, views), encoding="utf-8")
    # エージェント用のスキル。置いておけば、利用者は「スクショ作って」で済む
    skill_src = KIT / "skill" / "SKILL.md"
    skill_dst = root / ".claude" / "skills" / "bakeshot" / "SKILL.md"
    if skill_src.exists() and not skill_dst.exists():
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        skill_dst.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")
    for src_name, dst_name in [("agent_guide.md", "AGENT.md")]:
        g = KIT / src_name
        if g.exists():
            (d / dst_name).write_text(g.read_text(encoding="utf-8").replace("__MODULE__", module),
                                      encoding="utf-8")
    return f


def bake(root: Path, project: Path, app_target: str, locales, device: str,
         out_root: Path, bundle_id: str = "", strip_ext: bool = True,
         strip_ent: bool = False, team: str = "", keep: bool = False):
    features.pro()          # 完全版が入っていれば端末とウィジェットが増える
    if isinstance(locales, str):
        locales = [locales]
    locales = [l for l in locales if l] or ["ja"]
    module = scenes_mod.module_name(app_target)
    # Swift の識別子にならない名前（protoc-gen-swift のようなハイフン入り）は import できない
    _ok = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    imports = "".join(f"#if canImport({m})\nimport {m}\n#endif\n"
                      for m in sorted(scenes_mod.local_package_modules(root)) if _ok.match(m))
    scenes_file = ensure_scenes(root, module, imports)
    names = scenes_mod.names(scenes_file.read_text(encoding="utf-8"))
    if not names:
        raise SystemExit("台本に絵がありません。Bakeshot/Scenes.swift に shot / shotBoth を書いてください。")

    global _used_widgets
    token = uuid.uuid4().hex[:8]
    work = root / "Bakeshot" / ".work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    w, h, top, bottom, _px = devices.metrics(device)
    test = (KIT / "RenderTests.swift.template").read_text(encoding="utf-8")
    swift_locales = "[" + ", ".join('"%s"' % l.replace('"', '') for l in locales) + "]"
    for k, v in [("__IMPORTS__", imports), ("__MODULE__", module), ("__TOKEN__", token),
                 ("__LOCALES__", swift_locales),
                 ("__W__", str(w)), ("__H__", str(h)), ("__TOP__", str(top)), ("__BOTTOM__", str(bottom))]:
        test = test.replace(k, v)
    test_file = work / "RenderTests.swift"
    test_file.write_text(test, encoding="utf-8")
    api_file = work / "BakeshotSceneAPI.swift"
    api_file.write_text((KIT / "BakeshotSceneAPI.swift.template").read_text(encoding="utf-8"), encoding="utf-8")

    log(f"台本にある {len(names)} 枚を焼きます（{'・'.join(locales)} / {device}\"）"
        + (f" → {len(names) * len(locales)} 枚" if len(locales) > 1 else ""))
    # ウィジェットは公開版に処理が無い。台本に混ざっていると、
    # ウィジェットの型が見つからずビルドごと落ちる。**先に、はっきり止める。**
    if ".widget" in scenes_file.read_text(encoding="utf-8"):
        _used_widgets = True
    if not features.pro() and _used_widgets:
        raise SystemExit(
            "台本にウィジェットがあります。ウィジェットは完全版の機能です。\n"
            f"  買う:   {'https://bakeshot.lemonsqueezy.com'}\n"
            "  今すぐ焼くなら: Bakeshot/Scenes.swift から size: .widget… の行と、\n"
            "  そこで使っている下ごしらえを消してください（アプリの画面だけになります）。")

    # 1) xcodeproj を複製してテストターゲットを足す
    # 使い捨ての写し。**君のプロジェクトには一切書き込まない。**
    # 同じ場所に置くのは、xcodeproj の中のファイル参照が相対パスだから（動かすと全部壊れる）。
    # 先頭のドットで隠しておき、終わったら消す。
    dst = project.with_name("." + project.stem + "-bakeshot.xcodeproj")
    xcode.close_project(dst)
    code, out = xcode.run(["/usr/bin/env", "ruby", str(KIT / "add_test_target.rb"),
                           str(project), str(dst),
                           ":".join([str(test_file), str(api_file), str(scenes_file)]),
                           app_target, bundle_id, "1" if strip_ext else "0",
                           "1" if strip_ent else "0",
                           locales[0] if len(locales) == 1 else "", team,
                           str(work / "widget"), features.widget_support_rb()],
                          env_extra=xcode.UTF8)
    if code != 0:
        shutil.rmtree(dst, ignore_errors=True)
        if "cannot load such file -- xcodeproj" in out:
            raise SystemExit("Ruby の xcodeproj gem がありません。`gem install --user-install xcodeproj` を実行してください")
        raise SystemExit(f"xcodeproj の複製に失敗:\n{out[-800:]}")

    # 2) 先にビルドだけ通す（Xcode 経由だとコンパイルエラーが読めない）。
    #    引数が要る View が台本に混ざっていたら、その行を外して組み直す
    try:
        dest_id = xcode.mac_destination_id(dst)
    except SystemExit:
        shutil.rmtree(dst, ignore_errors=True)
        raise
    derived = work / "dd"
    pruned = []
    for attempt in range(1, 5):
        code, out = xcode.build_for_testing(dst, dest_id, derived)
        if code == 0:
            break
        errs = error_lines(out)
        lines = test_file.read_text(encoding="utf-8").splitlines()
        hits = failing_shot_lines(errs, lines)
        if not hits or attempt == 4:
            why = " / ".join(re.sub(r"^.*?: error: ", "", l) for l in errs[:4])
            if not keep:
                shutil.rmtree(dst, ignore_errors=True)
            raise SystemExit(f"ビルドに失敗しました:\n{why or out[-600:]}")
        dropped = []
        for n, name in hits:
            if name not in pruned:
                pruned.append(name)
            dropped.append(name)
            lines[n - 1] = ""
        test_file.write_text("\n".join(lines), encoding="utf-8")
        log(f"コンパイルが通らないので外しました: {', '.join(dropped)}", "!")
        for e in errs[:4]:
            log(re.sub(r"^.*?: error: ", "", e), " ")

    # 3) Xcode に走らせ、進捗ファイルで打ち切る。
    #    落ちる View があるとテストの完了が返ってこないので、Xcode の完了は当てにしない。
    for loc in locales:
        (out_root / loc).mkdir(parents=True, exist_ok=True)
    remaining = [n for n in names if n not in pruned]
    failed, collected, rounds = [], 0, 0
    got = {}                # 絵の名前 → 焼けた言語。全部そろって初めて「済」
    start_s = str(KIT / "start_test.applescript")
    stop_s = str(KIT / "stop_test.applescript")
    try:
        while remaining and rounds < len(names) + 2:
            rounds += 1
            log("Xcode で My Mac (Designed for iPad) を実行しています…" if rounds == 1
                else f"残り {len(remaining)} 枚でもう一周（{rounds} 回目）")
            box = find_out_dir(token)
            if box:
                for f in ("STATE", "LOG", "STDERR", "LOCALE"):
                    (box / f).unlink(missing_ok=True)
                # 落ちた絵は飛ばす。ソースではなくこのファイルで伝える（再ビルドを起こさない）
                # 撮影側は _light / _dark を落とした名前で見ている。合わせないと素通りする
                skips = skip_names(failed + pruned)
                (box / "SKIP").write_text("\n".join(skips), encoding="utf-8")
            code, out = xcode.osascript([start_s, str(dst), "BakeshotRender"])
            if "not loaded" in out:
                raise SystemExit("Xcode がプロジェクトを開けませんでした\n  うまくいかない時は、Xcode を一度終了してからやり直してください。")

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
            time.sleep(3)          # 止まり切る前に次を走らせると、Xcode が受け付けない
            if not box:
                raise SystemExit("Xcode でテストが始まりませんでした（ビルドが通っていない可能性）\n  うまくいかない時は、Xcode を一度終了してからやり直してください。")

            for loc in locales:
                sub = box / loc
                for f in (sorted(sub.glob("*.png")) if sub.is_dir() else []):
                    shutil.copy2(f, out_root / loc / f.name)
                    f.unlink()
                    collected += 1
                    got.setdefault(f.stem, set()).add(loc)
            done = {n for n, ls in got.items() if len(ls) == len(locales)}
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
                why = crash_reason(box)
                at = (box / "LOCALE").read_text(encoding="utf-8").strip() if (box / "LOCALE").exists() else ""
                log(f"✗ {parts[1]}{f'（{at}）' if at and len(locales) > 1 else ''} は焼いている最中に"
                    f"{'固まった' if parts[0] == 'TIMEOUT' else '落ちた'}ので外しました"
                    + (f"\n   {why}" if why else ""), "!")
            elif not last and not done:
                raise SystemExit(f"Xcode でテストが動きませんでした（{rounds} 回目）"
                             "  うまくいかない時は、Xcode を一度終了してからやり直してください。")
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
        shutil.rmtree(work / "dd", ignore_errors=True)

    log(f"{collected} 枚できました → {out_root}"
        + (f"/<{'・'.join(locales)}>" if len(locales) > 1 else f"/{locales[0]}"), "✓")
    if failed or pruned:
        log(f"焼けなかった: {', '.join(sorted(set(failed + pruned)))}", "!")
    return collected
