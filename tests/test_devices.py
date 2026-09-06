"""端末サイズ。数字を間違えるとストアに出せない絵ができる。"""
import unittest
from bakeshot import devices


class Metrics(unittest.TestCase):
    def test_every_listed_device_has_metrics(self):
        for name in devices.DEVICES:
            w, h, top, bottom, px = devices.metrics(name)
            self.assertGreater(w, 0, name)
            self.assertGreater(h, w, name)          # 縦長
            self.assertGreaterEqual(top, 0, name)
            self.assertGreaterEqual(bottom, 0, name)

    def test_default_is_a_known_device(self):
        self.assertIn(devices.DEFAULT, devices.DEVICES)

    def test_unknown_device_is_refused(self):
        with self.assertRaises(SystemExit):
            devices.metrics("4.7")
