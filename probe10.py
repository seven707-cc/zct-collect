#!/usr/bin/env python3
"""第十轮：用 r.jina.ai 服务端代理绕反爬，测 Reddit / Dcard / TikTok / IG。"""
from __future__ import annotations

import json
import urllib.parse

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}
Q = urllib.parse.quote("中餐厅")

TARGETS = [
    ("reddit_search", f"https://www.reddit.com/r/CDrama/search.json?q={Q}&restrict_sr=1&sort=relevance&limit=25"),
    ("reddit_all", f"https://www.reddit.com/search.json?q={Q}&limit=25"),
    ("dcard", f"https://www.dcard.tw/service/api/v2/search/posts?query={Q}"),
    ("tiktok_tag", f"https://www.tiktok.com/tag/{Q}"),
    ("instagram_tag", f"https://www.instagram.com/explore/tags/{Q}/"),
    ("ptt", f"https://www.ptt.cc/bbs/CN_Entertain/search?q={Q}"),
]


def jina(url: str, fmt: str = "text") -> tuple[int, str]:
    try:
        r = S.get("https://r.jina.ai/" + url, timeout=90,
                  headers={"X-Return-Format": fmt, "Accept": "*/*"})
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)[:200]


def main():
    out = {}
    for name, url in TARGETS:
        code, txt = jina(url)
        print(f"[{name}] jina={code} len={len(txt)}")
        print("   ", txt[:220].replace("\n", " "))
        out[name] = {"code": code, "len": len(txt), "head": txt[:1500]}
    RES = out
    with open("out/probe10.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
