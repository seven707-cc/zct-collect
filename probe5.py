#!/usr/bin/env python3
"""第五轮：① LIHKG 精确检索 ② Instagram 第三方镜像 ③ Dcard 变体。"""
from __future__ import annotations

import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
RES: dict = {}


def lihkg():
    out = {}
    for q in ["中餐廳9", "中餐廳 非洲", "丁禹兮", "黃曉明 中餐廳", "姜妍", "沈月 中餐廳"]:
        try:
            r = S.get("https://lihkg.com/api_v2/thread/search",
                      params={"q": q, "page": 1, "count": 30}, timeout=25,
                      headers={"Referer": "https://lihkg.com/", "X-Requested-With": "XMLHttpRequest"})
            items = ((r.json() or {}).get("response") or {}).get("items") or []
            print(f"[lihkg] {q}: {r.status_code} n={len(items)}")
            for it in items[:6]:
                print("   -", str(it.get("title"))[:70], "| 回覆", it.get("no_of_reply"))
            out[q] = items
        except Exception as e:
            print(f"[lihkg] {q} ERR {str(e)[:70]}")
    RES["lihkg"] = out


def ig_mirrors():
    out = {}
    targets = [
        ("imginn_tag", "https://imginn.com/tag/chineserestaurant/"),
        ("imginn_search", "https://imginn.com/search/?q=%E4%B8%AD%E9%A4%90%E5%8E%85"),
        ("picuki_tag", "https://www.picuki.com/tag/chineserestaurant"),
        ("dumpor_tag", "https://dumpor.com/v/tag/chineserestaurant"),
        ("greatfon_tag", "https://greatfon.com/tag/chineserestaurant"),
    ]
    for name, url in targets:
        try:
            r = S.get(url, timeout=25)
            shortcodes = set(re.findall(r'/(?:p|reel)/([A-Za-z0-9_-]{8,15})', r.text))
            print(f"[{name}] {r.status_code} len={len(r.content)} posts={len(shortcodes)}")
            if shortcodes:
                print("   sample:", list(shortcodes)[:5])
            out[name] = {"status": r.status_code, "len": len(r.content),
                         "posts": len(shortcodes), "codes": list(shortcodes)[:20]}
        except Exception as e:
            print(f"[{name}] ERR {str(e)[:70]}")
            out[name] = {"err": str(e)[:100]}
    RES["ig_mirrors"] = out


def dcard_variants():
    out = {}
    for url, params, hdr in [
        ("https://www.dcard.tw/v2/posts", {"search": "中餐廳"}, {}),
        ("https://www.dcard.tw/service/api/v2/search/posts", {"query": "中餐廳"}, {}),
        ("https://www.dcard.tw/service/api/v2/search/posts", {"query": "中餐廳"},
         {"x-requested-with": "XMLHttpRequest", "Origin": "https://www.dcard.tw"}),
    ]:
        tag = url.split("/")[-1] + str(len(hdr))
        try:
            r = S.get(url, params=params, headers=hdr, timeout=20)
            print(f"[dcard {tag}] {r.status_code} len={len(r.content)} {r.text[:120]}")
            out[tag] = {"status": r.status_code, "head": r.text[:200]}
        except Exception as e:
            print(f"[dcard {tag}] ERR {str(e)[:60]}")
    RES["dcard"] = out


def main():
    lihkg()
    ig_mirrors()
    dcard_variants()
    with open("out/probe5.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
