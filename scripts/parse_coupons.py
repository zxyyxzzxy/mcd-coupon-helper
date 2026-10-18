#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse_coupons.py — 把麦当劳 MCP 券包接口返回的 Markdown 文本解析成结构化 JSON。

背景：`query-my-coupons` 和 `available-coupons` 返回的不是 JSON，而是供大模型阅读的
Markdown 文本（含 `<img>` 标签）。要把它接入程序、做定时任务或算价，必须先结构化。

纯标准库，无第三方依赖。Python 3.8+。

用法：
    python3 scripts/parse_coupons.py fixtures/coupons_sample.md
    python3 scripts/parse_coupons.py --now "2026-10-19T08:00:00" fixtures/coupons_sample.md
    cat out.md | python3 scripts/parse_coupons.py -

输出：JSON 数组，每张券一个对象，字段见 README「数据模型」一节。
"""

import argparse
import json
import re
import sys
from datetime import datetime, date, time

# 有效期形如：2026-10-19 10:30-2026-10-23 23:59 周一、二、三、四、五 10:30-23:59
DATE_RANGE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})"
)
# 星期段：周一、二、三 / 周一至周五 / 周一
# 注意：枚举分支必须吃掉分隔符，否则「周一至周五」会被枚举分支的零次重复提前截断成「周一」
WEEKDAY_RE = re.compile(
    r"周([一二三四五六日天](?:\s*(?:[、,，]\s*周?[一二三四五六日天]|[至到]\s*周?[一二三四五六日天]))*)"
)
# 每日可用时段：10:00-22:00
WINDOW_RE = re.compile(r"(?<!\d)(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})(?!\d)")
PRICE_RE = re.compile(r"¥\s*([0-9]+(?:\.[0-9]+)?)")
FIELD_RE = re.compile(r"^-\s*\*\*(.+?)\*\*\s*[:：]\s*(.*)$")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
IMG_RE = re.compile(r"<img[^>]*>", re.IGNORECASE)

WEEKDAY_INDEX = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


def _parse_weekdays(text):
    """解析星期约束，返回 [0-6]（周一=0）；无约束返回 None。"""
    m = WEEKDAY_RE.search(text)
    if not m:
        return None
    body = m.group(1)
    sep = re.search(r"[至到]", body)
    if sep:
        start = WEEKDAY_INDEX.get(body[sep.start() - 1])
        rest = body[sep.end():].replace("周", "").strip()
        end = WEEKDAY_INDEX.get(rest[0]) if rest else None
        if start is None or end is None:
            return None
        if start <= end:
            return list(range(start, end + 1))
        return list(range(start, 7)) + list(range(0, end + 1))
    days = []
    for ch in body:
        if ch in WEEKDAY_INDEX:
            days.append(WEEKDAY_INDEX[ch])
    # 去重保序
    seen, out = set(), []
    for d in days:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out or None


def _parse_validity(raw):
    """把有效期原文拆成起止日期、星期约束、每日时段。"""
    result = {
        "valid_from": None,
        "valid_to": None,
        "weekdays": None,
        "daily_window": None,
        "raw": raw,
    }
    if not raw:
        return result

    m = DATE_RANGE_RE.search(raw)
    rest = raw
    if m:
        result["valid_from"] = "%s %s" % (m.group(1), m.group(2))
        result["valid_to"] = "%s %s" % (m.group(3), m.group(4))
        rest = raw[: m.start()] + " " + raw[m.end():]

    result["weekdays"] = _parse_weekdays(rest)

    w = WINDOW_RE.search(rest)
    if w:
        result["daily_window"] = "%s-%s" % (w.group(1), w.group(2))

    return result


def _to_dt(text, fmt="%Y-%m-%d %H:%M"):
    if not text:
        return None
    try:
        return datetime.strptime(text, fmt)
    except ValueError:
        return None


def _usable_at(coupon, now):
    """判断某张券在 now 这一刻是否可用（日期区间 + 星期 + 每日时段三重约束）。"""
    v = coupon["validity"]
    start = _to_dt(v["valid_from"])
    end = _to_dt(v["valid_to"])
    if start is None or end is None:
        return None
    if now < start or now > end:
        return False
    if v["weekdays"] is not None and now.weekday() not in v["weekdays"]:
        return False
    if v["daily_window"]:
        w_start, w_end = v["daily_window"].split("-")
        t_start = datetime.strptime(w_start, "%H:%M").time()
        t_end = datetime.strptime(w_end, "%H:%M").time()
        cur = now.time()
        if t_start <= t_end:
            if not (t_start <= cur <= t_end):
                return False
        else:  # 跨零点时段
            if not (cur >= t_start or cur <= t_end):
                return False
    return True


def parse(text, now=None):
    """解析券列表 Markdown，返回券对象列表。"""
    coupons = []
    blocks = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        if not name:
            continue

        coupon = {
            "name": name,
            "coupon_price": None,
            "validity": _parse_validity(""),
            "received_at": None,
            "tags": [],
            "channels": [],
            "expiring_today": False,
        }

        for line in lines[1:]:
            m = FIELD_RE.match(line.strip())
            if m:
                key, value = m.group(1).strip(), m.group(2).strip()
                if "优惠" in key or "价格" in key:
                    p = PRICE_RE.search(value)
                    if p:
                        coupon["coupon_price"] = float(p.group(1))
                elif "有效期" in key:
                    coupon["validity"] = _parse_validity(value)
                elif "领取时间" in key:
                    coupon["received_at"] = value or None
                elif "标签" in key:
                    tags = [t.strip() for t in re.split(r"[、,，]", value) if t.strip()]
                    coupon["tags"] = tags
                    coupon["expiring_today"] = any("今日到期" in t for t in tags)
                    coupon["channels"] = [
                        t.replace("专用", "") for t in tags if "专用" in t
                    ]
            elif IMG_RE.search(line):
                # 图片标签只用于展示，不进入结构化数据
                continue

        coupons.append(coupon)

    if now is not None:
        for c in coupons:
            c["usable_now"] = _usable_at(c, now)
            c["days_left"] = _days_left(c, now)

    return coupons


def _days_left(coupon, now):
    end = _to_dt(coupon["validity"]["valid_to"])
    if end is None:
        return None
    return (end.date() - now.date()).days


def main(argv=None):
    ap = argparse.ArgumentParser(description="解析麦当劳 MCP 券包 Markdown 为 JSON")
    ap.add_argument("path", help="Markdown 文件路径，'-' 表示从标准输入读取")
    ap.add_argument(
        "--now",
        default=None,
        help="用于判断可用性的基准时间，ISO 格式，如 2026-10-19T08:30:00；默认本地当前时间",
    )
    args = ap.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as fh:
            text = fh.read()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    coupons = parse(text, now=now)
    json.dump(
        {"count": len(coupons), "parsed_at": now.strftime("%Y-%m-%d %H:%M"), "coupons": coupons},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
