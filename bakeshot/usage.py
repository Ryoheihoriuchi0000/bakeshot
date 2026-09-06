"""焼いた回数だけを数える。断れる。

送るのは「いつ・何枚焼いたか」だけ。プロジェクト名もパスもコードも送らない。
何が起きるかを最初に見せて、断られたら二度と送らない。
"""
import json
import platform
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ENDPOINT = "https://bakeshot.vercel.app/api/ping"
STORE = Path.home() / ".bakeshot" / "state.json"

NOTICE = """\
Bakeshot は、焼いた回数だけを数えさせてもらえると助かります。
送るのは次の3つだけです。プロジェクト名・パス・コード・画像は送りません。

  · 端末ごとのランダムな id（あなたが誰かは分かりません）
  · 焼いた日と枚数、言語の数、ウィジェットを使ったか
  · Bakeshot と macOS の版

料金の形（年額か月額か）を、憶測ではなく実際の使われ方で決めたいので集めています。
いつでも `bakeshot usage off` で止められます。
"""


def _load():
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_enabled(on: bool):
    d = _load()
    d["usage"] = bool(on)
    _save(d)


def state() -> str:
    d = _load()
    return "on" if d.get("usage") is True else ("off" if d.get("usage") is False else "未設定")


def _ask() -> bool:
    """初回だけ聞く。端末が対話でなければ送らない。"""
    import sys
    if not sys.stdin.isatty():
        return False
    print(NOTICE)
    try:
        ans = input("送っていいですか [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return ans in ("y", "yes")


def send(*, shots: int, locales: int, widgets: bool):
    d = _load()
    if "usage" not in d:
        d = _load()
        d["usage"] = _ask()
        if "id" not in d:
            d["id"] = uuid.uuid4().hex
        _save(d)
    if not d.get("usage"):
        return
    if not d.get("id"):
        d["id"] = uuid.uuid4().hex
        _save(d)

    from . import __version__ as ver
    body = json.dumps({
        "id": d["id"],
        "ver": ver,
        "os": platform.mac_ver()[0].split(".")[0],
        "shots": shots,
        "locales": locales,
        "widgets": bool(widgets),
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    try:                       # 届かなくても焼き上がりには関係ない
        urllib.request.urlopen(req, timeout=4).read()
    except Exception:
        pass
