#!/usr/bin/env python3
"""探测在 GitHub runner 上哪些海外平台接口能拿到「中餐厅9」相关数据。"""
from __future__ import annotations

import json

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})

TESTS: list[tuple[str, str, dict | None]] = [
    ("reddit_search", "https://www.reddit.com/r/CDrama/search.json",
     {"q": "Chinese Restaurant", "restrict_sr": 1, "limit": 10, "sort": "relevance"}),
    ("reddit_api_search", "https://api.reddit.com/search.json",
     {"q": "Chinese Restaurant S9", "limit": 10}),
    ("reddit_old", "https://old.reddit.com/r/CDrama/search.json",
     {"q": "中餐厅", "restrict_sr": 1, "limit": 10}),
    ("tikwm_search", "https://www.tikwm.com/api/feed/search",
     {"keywords": "chinese restaurant 9", "count": 10, "cursor": 0}),
    ("tiktok_web", "https://www.tiktok.com/api/search/general/full",
     {"keyword": "中餐厅9", "count": 10}),
    ("instagram_tag", "https://www.instagram.com/api/v1/tags/web_info/",
     {"tag_name": "chineserestaurant"}),
    ("dailymotion", "https://api.dailymotion.com/videos",
     {"search": "Chinese Restaurant MangoTV", "limit": 5, "fields": "id,title,url"}),
    ("mydramalist", "https://mydramalist.com/search",
     {"q": "Chinese Restaurant"}),
    ("viki", "https://api.viki.io/v4/search.json",
     {"q": "Chinese Restaurant", "per_page": 5}),
    ("threads", "https://www.threads.net/api/graphql", None),
    ("nitter_nitterpo", "https://nitter.poast.org/search",
     {"f": "tweets", "q": "中餐厅9"}),
    ("nitter_xcancel", "https://xcancel.com/search",
     {"f": "tweets", "q": "Chinese Restaurant 9"}),
    ("youtube_discussion", "https://www.youtube.com/watch",
     {"v": "MU0qexL9obc"}),
    ("douban_intl", "https://m.douban.com/review/search",
     {"q": "中餐厅"}),
    ("quora", "https://www.quora.com/search",
     {"q": "Chinese Restaurant MangoTV"}),
]


def main() -> None:
    out = []
    for name, url, params in TESTS:
        try:
            r = S.get(url, params=params, timeout=20, allow_redirects=True)
            ct = r.headers.get("content-type", "")
            body = r.text[:300].replace("\n", " ")
            n = 0
            if "json" in ct:
                try:
                    d = r.json()
                    n = len(d.get("data", {}).get("children", []) if isinstance(d, dict) else [])
                except Exception:
                    pass
            print(f"[{name}] {r.status_code} ct={ct[:30]} len={len(r.content)} n={n}")
            print(f"   {body[:200]}")
            out.append({"name": name, "status": r.status_code, "len": len(r.content),
                        "ct": ct[:40], "head": body[:200]})
        except Exception as e:
            print(f"[{name}] ERR {str(e)[:90]}")
            out.append({"name": name, "status": "ERR", "err": str(e)[:120]})

    with open("out/probe_platforms.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
