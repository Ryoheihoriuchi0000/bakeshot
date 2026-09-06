"""完全版（bakeshot_pro）があれば読み込む。

公開版には完全版の処理そのものが入っていない。**確認を消せば使える、という作りにしない。**
"""
_loaded = None


def pro():
    """完全版が入っているか。入っていればウィジェットが焼ける。"""
    global _loaded
    if _loaded is None:
        try:
            import bakeshot_pro
            bakeshot_pro.install()
            _loaded = True
        except Exception:
            _loaded = False
    return _loaded


def widget_support_rb():
    """ウィジェットのソースを取り込む Ruby の断片。公開版には無い。"""
    if not pro():
        return ""
    import bakeshot_pro
    return bakeshot_pro.widget_support_rb()


def upsell(what: str) -> str:
    return (f"{what} は完全版の機能です。\n"
            f"  → https://bakeshot.lemonsqueezy.com\n"
            f"  買ったら: pip install <届いた wheel> && bakeshot activate <鍵>")
