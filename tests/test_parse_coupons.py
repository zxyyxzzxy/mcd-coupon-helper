#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析器测试。运行：python3 -m unittest discover -s tests -v"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from parse_coupons import parse, _parse_weekdays, _parse_validity  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "coupons_sample.md")


def load():
    with open(FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class TestValidityParsing(unittest.TestCase):
    def test_plain_range(self):
        v = _parse_validity("2026-10-19 00:00-2026-10-25 23:59")
        self.assertEqual(v["valid_from"], "2026-10-19 00:00")
        self.assertEqual(v["valid_to"], "2026-10-25 23:59")
        self.assertIsNone(v["weekdays"])
        self.assertIsNone(v["daily_window"])

    def test_range_with_weekdays_and_window(self):
        v = _parse_validity(
            "2026-10-19 10:30-2026-10-23 23:59 周一、二、三、四、五 10:30-23:59"
        )
        self.assertEqual(v["weekdays"], [0, 1, 2, 3, 4])
        self.assertEqual(v["daily_window"], "10:30-23:59")

    def test_single_day_breakfast(self):
        v = _parse_validity("2026-10-19 05:00-2026-10-19 10:29 周一 05:00-10:29")
        self.assertEqual(v["valid_from"], "2026-10-19 05:00")
        self.assertEqual(v["valid_to"], "2026-10-19 10:29")
        self.assertEqual(v["weekdays"], [0])
        self.assertEqual(v["daily_window"], "05:00-10:29")

    def test_window_without_weekdays(self):
        v = _parse_validity("2026-10-19 00:00-2026-10-25 23:59 10:00-22:00")
        self.assertIsNone(v["weekdays"])
        self.assertEqual(v["daily_window"], "10:00-22:00")

    def test_weekday_range_notation(self):
        self.assertEqual(_parse_weekdays("周一至周五"), [0, 1, 2, 3, 4])

    def test_weekend_only(self):
        self.assertEqual(_parse_weekdays("周六、周日"), [5, 6])


class TestCouponList(unittest.TestCase):
    def setUp(self):
        self.coupons = parse(load(), now=datetime(2026, 10, 19, 8, 0))
        self.by_name = {c["name"]: c for c in self.coupons}

    def test_count(self):
        self.assertEqual(len(self.coupons), 7)

    def test_price_parsed(self):
        self.assertEqual(self.by_name["9.9元中杯冰美式"]["coupon_price"], 9.9)
        self.assertEqual(self.by_name["人气麦旋风买一送一"]["coupon_price"], 15.0)

    def test_missing_received_at_is_none_not_error(self):
        # 早餐券的返回里没有「领取时间」字段，必须容忍缺失
        c = self.by_name["火腿扒堡早餐两件套"]
        self.assertIsNone(c["received_at"])

    def test_expiring_today_flag(self):
        self.assertTrue(self.by_name["火腿扒堡早餐两件套"]["expiring_today"])
        self.assertFalse(self.by_name["芝香脆鸡扒堡早餐两件套"]["expiring_today"])

    def test_dual_channel(self):
        c = self.by_name["9.9元中杯冰美式"]
        self.assertEqual(c["channels"], ["到店", "外送"])

    def test_single_channel(self):
        self.assertEqual(self.by_name["人气麦旋风买一送一"]["channels"], ["到店"])

    def test_markdown_img_not_leaked(self):
        for c in self.coupons:
            self.assertNotIn("<img", str(c))

    def test_days_left(self):
        self.assertEqual(self.by_name["火腿扒堡早餐两件套"]["days_left"], 0)
        self.assertEqual(self.by_name["9.9元中杯冰美式"]["days_left"], 6)


class TestUsability(unittest.TestCase):
    """同一批券在不同时间点的可用性必须不同，这是最容易写错的地方。"""

    def usable(self, name, dt):
        coupons = parse(load(), now=dt)
        return {c["name"]: c for c in coupons}[name]["usable_now"]

    def test_breakfast_window(self):
        self.assertTrue(self.usable("火腿扒堡早餐两件套", datetime(2026, 10, 19, 8, 0)))
        self.assertFalse(self.usable("火腿扒堡早餐两件套", datetime(2026, 10, 19, 11, 0)))
        self.assertFalse(self.usable("火腿扒堡早餐两件套", datetime(2026, 10, 19, 4, 59)))

    def test_weekday_constraint(self):
        # 10-24 是周六，麦辣鸡腿堡券限定周一至周五
        self.assertFalse(self.usable("11.9元麦辣鸡腿堡", datetime(2026, 10, 24, 12, 0)))
        self.assertTrue(self.usable("11.9元麦辣鸡腿堡", datetime(2026, 10, 19, 12, 0)))

    def test_start_time_not_reached(self):
        self.assertFalse(self.usable("11.9元麦辣鸡腿堡", datetime(2026, 10, 19, 10, 0)))
        self.assertTrue(self.usable("11.9元麦辣鸡腿堡", datetime(2026, 10, 19, 10, 30)))

    def test_daily_window(self):
        self.assertFalse(self.usable("人气麦旋风买一送一", datetime(2026, 10, 19, 9, 59)))
        self.assertTrue(self.usable("人气麦旋风买一送一", datetime(2026, 10, 19, 10, 30)))

    def test_expired(self):
        self.assertFalse(self.usable("9.9元中杯冰美式", datetime(2026, 10, 26, 0, 1)))


if __name__ == "__main__":
    unittest.main()
