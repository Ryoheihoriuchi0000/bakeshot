"""回数の送信。既定では送らない、断ったら二度と送らない、を守る。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bakeshot import usage


class Consent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "state.json"
        self.patch = mock.patch.object(usage, "STORE", self.store)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_unset_by_default(self):
        self.assertEqual(usage.state(), "未設定")

    def test_off_stays_off_and_sends_nothing(self):
        usage.set_enabled(False)
        self.assertEqual(usage.state(), "off")
        with mock.patch.object(usage.urllib.request, "urlopen") as opened:
            usage.send(shots=3, locales=1, widgets=False)
            opened.assert_not_called()

    def test_never_asks_when_not_a_terminal(self):
        # CI で勝手に送らない。聞けない場所では送らない
        with mock.patch("sys.stdin.isatty", return_value=False), \
             mock.patch.object(usage.urllib.request, "urlopen") as opened:
            usage.send(shots=1, locales=1, widgets=False)
            opened.assert_not_called()
        self.assertEqual(usage.state(), "off")

    def test_on_sends_only_the_agreed_fields(self):
        usage.set_enabled(True)
        sent = {}

        def fake(req, timeout=0):
            sent.update(json.loads(req.data.decode()))
            class R:
                def read(self): return b""
                def __enter__(self): return self
                def __exit__(self, *a): return False
            return R()

        with mock.patch.object(usage.urllib.request, "urlopen", fake):
            usage.send(shots=5, locales=2, widgets=True)
        self.assertEqual(set(sent), {"id", "ver", "os", "shots", "locales", "widgets"})
        self.assertEqual(sent["shots"], 5)
        self.assertTrue(sent["widgets"])

    def test_a_failed_send_is_swallowed(self):
        usage.set_enabled(True)
        with mock.patch.object(usage.urllib.request, "urlopen", side_effect=OSError("no net")):
            usage.send(shots=1, locales=1, widgets=False)   # 焼き上がりに影響させない
