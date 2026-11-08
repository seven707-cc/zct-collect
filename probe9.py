#!/usr/bin/env python3
"""第九轮：PTT 网页镜像（pttweb）——台综讨论 + 推嘘。"""
from __future__ import annotations

import json
import re
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}
Q = "中餐廳"


def try_url(tag: str, url: str) -> str:
    try:
        r = S.get(url, timeout=25)
        print(f"[{tag}] {r.status_code} len={len(r.content)}")
        return r.text if r.status_code == 200 else ""
    except Exception as e:
        print(f"[{tag}] ERR {str(e)[:70]}")
        return ""


def main():
    q = urllib.parse.quote(Q)
    targets = [
        ("search", f"https://www.pttweb.cc/search?q={q}"),
        ("board_cn", "https://www.pttweb.cc/bbs/CN_Entertain"),
        ("board_tw", "https://www.pttweb.cc/bbs/TW_Entertain"),
        ("alt_domain", f"https://pttweb.tw/search?q={q}"),
    ]
    for tag, url in targets:
        html = try_url(tag, url)
        if not html:
            RES[tag] = {"fail": True}
            continue
        links = re.findall(r'href="(/bbs/[A-Za-z0-9_]+/[^"]+)"[^>]*>([^<]{4,80})<', html)
        hits = [x for x in links if "中餐" in x[1] or "中餐廳" in x[1]]
        print(f"   links={len(links)} 中餐相关={len(hits)}")
        for h in hits[:10]:
            print("     -", h[1][:70], h[0][:50])
        RES[tag] = {"links": len(links),
                    "hits": [{"url": h[0], "title": h[1]} for h in hits[:40]],
                    "sample": [x[1][:60] for x in links[:10]]}
    with open("out/probe9.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
