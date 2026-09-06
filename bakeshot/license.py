"""鍵。

守っているのは機能ではなく「更新が続くこと」。中身が読める以上、確認を消すのは誰にでもできる。
それでも成立するのは、仕事でリリースを回している人が毎回のスクショ作りを消したいからで、
そういう人は割らない。**だから確認は淡々と、邪魔にならない形にする。**
"""
import json
import platform
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.lemonsqueezy.com/v1/licenses"
STORE = Path.home() / ".bakeshot" / "state.json"
BUY = "https://bakeshot.lemonsqueezy.com"


def _load():
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _post(path, **fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(f"{API}/{path}", data=body,
                                 headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def activate(key: str) -> str:
    """鍵を有効にする。成功したら控えを置いて、以後はネット無しでも通す。"""
    try:
        res = _post("activate", license_key=key, instance_name=platform.node() or "mac")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"鍵を確認できませんでした（{e.code}）。鍵が正しいか、購入ページの案内を見てください。")
    except Exception as e:
        raise SystemExit(f"鍵の確認に失敗しました: {e}")
    if not res.get("activated"):
        raise SystemExit(res.get("error") or "この鍵は使えません。")
    d = _load()
    d["license"] = {"key": key,
                    "instance": (res.get("instance") or {}).get("id"),
                    "activated_on": date.today().isoformat()}
    _save(d)
    name = ((res.get("meta") or {}).get("product_name")) or "Bakeshot"
    return name


def licensed() -> bool:
    return bool(_load().get("license", {}).get("key"))


def status() -> str:
    lic = _load().get("license")
    return (f"ライセンス済み（{lic.get('activated_on')} から）" if lic
            else "ライセンスなし")
