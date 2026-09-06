"""bakeshot — シミュレータも UI テストも無しで、アプリの実UIを焼く。"""
import argparse
import json
import sys
from pathlib import Path

from . import __version__, bake as bake_mod, devices, doctor as doctor_mod, features, license as license_mod, scenes as scenes_mod


def find_project(root: Path):
    cands = [p for p in root.glob("*.xcodeproj") if not p.name.endswith("-Bakeshot.xcodeproj")]
    if not cands:
        raise SystemExit(f"{root} に .xcodeproj がありません")
    return sorted(cands)[0]


def load_config(root: Path):
    f = root / "Bakeshot" / "bakeshot.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_config(root: Path, cfg):
    d = root / "Bakeshot"
    d.mkdir(parents=True, exist_ok=True)
    (d / "bakeshot.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


NEXT_STEPS = """
用意できました。あとはエージェント（Claude Code / Cursor など）にこう言ってください。

  Bakeshot で App Store 用のスクショを作って

スキルを .claude/skills/bakeshot/ に置いたので、エージェントが台本を書いて焼くところまで
やります。Cursor など Claude Code 以外を使っているなら、代わりにこう言ってください。

  .claude/skills/bakeshot/SKILL.md を読んで、その通りにやって
"""


def cmd_init(args):
    root = Path(args.path).resolve()
    project = find_project(root)
    target = args.target or project.stem
    cfg = load_config(root)
    cfg.update({"project": project.name, "target": target,
                "locales": cfg.get("locales", ["ja"]),
                "devices": cfg.get("devices", [devices.DEFAULT])})
    save_config(root, cfg)
    module = target.replace("-", "_")
    imports = "".join(f"#if canImport({m})\nimport {m}\n#endif\n"
                      for m in sorted(scenes_mod.local_package_modules(root)))
    if not doctor_mod.report(root, quiet_when_ok=True):
        raise SystemExit(1)
    bake_mod.ensure_scenes(root, module, imports)
    print(NEXT_STEPS)


def cmd_doctor(args):
    ok = doctor_mod.report(Path(args.path).resolve())
    raise SystemExit(0 if ok else 1)


def cmd_bake(args):
    features.pro()          # 端末の一覧は完全版の有無で変わる
    root = Path(args.path).resolve()
    # 足りないものは、時間を使う前に言う
    if not doctor_mod.report(root, quiet_when_ok=True):
        raise SystemExit(1)
    cfg = load_config(root)
    project = root / cfg["project"] if cfg.get("project") else find_project(root)
    target = args.target or cfg.get("target") or project.stem
    locales = args.locale or cfg.get("locales") or ["ja"]
    devs = args.device or cfg.get("devices") or [devices.DEFAULT]
    out_root = Path(args.out).resolve() if args.out else root / "Bakeshot" / "out"
    total = 0
    for dev in devs:
        for loc in locales:
            sub = out_root / dev if len(devs) > 1 else out_root
            total += bake_mod.bake(root, project, target, loc, dev, sub,
                                   bundle_id=args.bundle_id or cfg.get("bundleId", ""),
                                   strip_ext=not args.keep_extensions,
                                   strip_ent=args.strip_entitlements or cfg.get("stripEntitlements", False),
                                   team=args.team or cfg.get("team", ""),
                                   keep=args.keep_project)
    print(f"\n合計 {total} 枚")


def cmd_activate(args):
    name = license_mod.activate(args.key.strip())
    print(f"{name} を有効にしました。ありがとうございます。")


def cmd_status(args):
    features.pro()
    print(("完全版" if features.pro() else "公開版") +
          f" / 端末サイズ: {', '.join(devices.DEVICES)}" +
          f" / ウィジェット: {'あり' if features.pro() else 'なし'}")
    print(license_mod.status())


def main(argv=None):
    p = argparse.ArgumentParser(prog="bakeshot", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="撮影台本の下書きと設定を置く")
    i.add_argument("path", nargs="?", default=".")
    i.add_argument("--target", help="アプリのターゲット名（既定: xcodeproj の名前）")
    i.set_defaults(func=cmd_init)

    d = sub.add_parser("doctor", help="足りないものを調べる")
    d.add_argument("path", nargs="?", default=".")
    d.set_defaults(func=cmd_doctor)

    b = sub.add_parser("bake", help="台本どおりに焼く")
    b.add_argument("path", nargs="?", default=".")
    b.add_argument("--target")
    b.add_argument("--locale", action="append", help="言語（繰り返し指定可。例: --locale ja --locale en）")
    b.add_argument("--device", action="append",
                   help=f"端末サイズ（既定: {devices.DEFAULT}。使えるのは "
                        f"{', '.join(devices.DEVICES)}）")
    b.add_argument("--out", help="書き出し先（既定: Bakeshot/out）")
    b.add_argument("--bundle-id", help="bundle id を差し替える（他人のプロジェクト用）")
    b.add_argument("--team", help="署名するチーム ID")
    b.add_argument("--strip-entitlements", action="store_true", help="entitlements を剥がす")
    b.add_argument("--keep-extensions", action="store_true", help="拡張ターゲットを複製に残す")
    b.add_argument("--keep-project", action="store_true", help="作った *-Bakeshot.xcodeproj を消さない")
    b.set_defaults(func=cmd_bake)

    a = sub.add_parser("activate", help="買った鍵を入れる")
    a.add_argument("key")
    a.set_defaults(func=cmd_activate)

    st = sub.add_parser("status", help="お試しの残りとライセンスの状態")
    st.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n中断しました", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
