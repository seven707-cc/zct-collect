#!/usr/bin/env python3
"""第七轮：文学城 / HK01 / Uwants 站内搜索「中餐厅」。"""
from __future__ import annotations

import json
import re
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
RES: dict = {}
Q = "中餐厅"


def titles(html: str, pattern: str, n: int = 12):
    out = re.findall(pattern, html, re.S)
    return [re.sub(r"<[^>]+>", "", t).strip()[:80] for t in out[:n]]


def wxc():
    out = {}
    for name, url in [
        ("wxc_search", f"https://www.wenxuecity.com/search?q={urllib.parse.quote(Q)}"),
        ("bbs_search", f"https://bbs.wenxuecity.com/search/?q={urllib.parse.quote(Q)}"),
        ("bbs_filmtv", "https://bbs.wenxuecity.com/tv/"),
    ]:
        try:
            r = S.get(url, timeout=25)
            ts = titles(r.text, r'<a[^>]+href="([^"]*?)"[^>]*>([^<]{4,60}中[^<]{0,40})</a>')
            hits = re.findall(r"[^>]{0,10}(中餐厅[^<]{0,40})", r.text)
            print(f"[{name}] {r.status_code} len={len(r.content)} 中餐厅命中={len(hits)}")
            for h in hits[:8]:
                print("    -", h[:70])
            out[name] = {"status": r.status_code, "hits": hits[:30]}
        except Exception as e:
            print(f"[{name}] ERR {str(e)[:60]}")
    RES["wenxuecity"] = out


def hk01():
    out = {}
    for url in [f"https://www.hk01.com/search?q={urllib.parse.quote(Q)}",
                f"https://www.hk01.com/api/search?q={urllib.parse.quote(Q)}"]:
        try:
            r = S.get(url, timeout=25)
            hits = re.findall(r"[^>]{0,10}(中餐廳[^<]{0,50})", r.text)
            print(f"[hk01] {r.status_code} len={len(r.content)} 命中={len(hits)}")
            for h in hits[:8]:
                print("    -", h[:70])
            out[url] = {"status": r.status_code, "hits": hits[:30]}
        except Exception as e:
            print(f"[hk01] ERR {str(e)[:60]}")
    RES["hk01"] = out


def uwants():
    out = {}
    for url in ["https://www.uwants.com/forumdisplay.php?fid=659",
                "https://www.uwants.com/search.php?srchtxt=" + urllib.parse.quote(Q),
                "https://www.uwants.com/forum.php?mod=forumdisplay&fid=659"]:
        try:
            r = S.get(url, timeout=25)
            hits = re.findall(r"[^>]{0,6}(中餐廳[^<]{0,50})", r.text)
            print(f"[uwants] {url[-40:]} {r.status_code} len={len(r.content)} 命中={len(hits)}")
            for h in hits[:5]:
                print("    -", h[:70])
            out[url] = {"status": r.status_code, "hits": hits[:20]}
        except Exception as e:
            print(f"[uwants] ERR {str(e)[:60]}")
    RES["uwants"] = out


def main():
    wxc()
    hk01()
    uwants()
    with open("out/probe7.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
