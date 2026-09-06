"""端末の寸法（pt）。Probe アプリで実機から測った値。

公開版は 6.9" だけ。他のサイズは完全版（bakeshot_pro）が足す。
"""

# 名前: (幅, 高さ, 上のセーフエリア, 下のセーフエリア, 書き出す画素)
DEVICES = {
    "6.9": (440, 956, 62, 34, (1320, 2868)),
}
DEFAULT = "6.9"


def register(name, spec):
    """完全版から端末を足す。"""
    DEVICES[name] = spec


def metrics(name: str):
    if name not in DEVICES:
        from . import features
        extra = "" if features.pro() else (
            "\n  6.9\" 以外は完全版が要ります → https://bakeshot.lemonsqueezy.com")
        raise SystemExit(f"知らない端末です: {name}（使えるのは {', '.join(DEVICES)}）{extra}")
    return DEVICES[name]
