#!/usr/bin/env python3
"""采集 Reddit 上关于《中餐厅9》的帖子与全部评论（经 arctic-shift 归档 API）。

arctic-shift 限制：posts/search 带 query 时必须给 subreddit，且频率过高会 422，
所以逐个请求 + 退避重试。
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
AS = "https://arctic-shift.photon-reddit.com/api"

SUBS = ["CDrama", "ChineseTV", "asiandrama", "Cantonese", "MangoTV",
        "ChineseLanguage", "variety_shows", "China"]
QUERIES = ["中餐厅", "Chinese Restaurant", "MangoTV", "Ding Yuxi", "Huang Xiaoming"]

KEEP = re.compile(r"中餐厅|中餐廳|chinese restaurant|mango\s*tv|丁禹兮|黄晓明|姜妍|沈月|"
                  r"ding yuxi|huang xiaoming|shen yue|jiang yan|patrick", re.I)


def get(path: str, params: dict, tries: int = 4) -> dict:
    for i in range(tries):
        try:
            r = S.get(f"{AS}{path}", params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 422:
                time.sleep(3 + i * 3)
                continue
            if r.status_code == 429:
                time.sleep(10 + i * 10)
                continue
            print(f"  {path} HTTP {r.status_code} {r.text[:120]}")
            return {}
        except Exception as e:
            print(f"  {path} ERR {str(e)[:70]}")
            time.sleep(2 + i * 2)
    return {}


def iso(ts) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(ts)))
    except Exception:
        return ""


def main() -> None:
    os.makedirs("out", exist_ok=True)
    posts: dict[str, dict] = {}
    for sub in SUBS:
        for q in QUERIES:
            d = get("/posts/search", {"subreddit": sub, "query": q, "limit": 100,
                                      "sort": "desc"})
            items = d.get("data") or []
            n0 = len(posts)
            for p in items:
                pid = p.get("id")
                if not pid or pid in posts:
                    continue
                text = f"{p.get('title','')} {p.get('selftext','')}"
                if not KEEP.search(text):
                    continue
                posts[pid] = p
            print(f"[{sub}/{q}] 返回{len(items)} 新增{len(posts)-n0} 累计{len(posts)}")
            time.sleep(1.2)

    print(f"\n命中帖子 {len(posts)} 条")
    rows: list[dict] = []
    for i, (pid, p) in enumerate(posts.items(), 1):
        title = p.get("title", "")
        body = p.get("selftext", "") or ""
        if body.strip():
            rows.append({
                "platform": "Reddit", "platform_region": "海外",
                "video_id": pid, "video_title": title,
                "cid": f"{pid}_post", "publish_time": iso(p.get("created_utc")),
                "user_name": p.get("author", ""), "user_region": "",
                "text": body.strip(), "like": int(p.get("score") or 0),
                "reply_count": int(p.get("num_comments") or 0),
                "parent_cid": "", "raw": {"subreddit": p.get("subreddit"),
                                          "permalink": p.get("permalink"), "kind": "post"},
            })
        d = get("/comments/search", {"link_id": pid, "limit": 100})
        cs = d.get("data") or []
        for c in cs:
            txt = (c.get("body") or "").strip()
            if not txt or txt in ("[deleted]", "[removed]"):
                continue
            rows.append({
                "platform": "Reddit", "platform_region": "海外",
                "video_id": pid, "video_title": title,
                "cid": c.get("id", ""), "publish_time": iso(c.get("created_utc")),
                "user_name": c.get("author", ""), "user_region": "",
                "text": txt, "like": int(c.get("score") or 0), "reply_count": 0,
                "parent_cid": c.get("parent_id", ""),
                "raw": {"subreddit": c.get("subreddit"), "kind": "comment"},
            })
        print(f"[{i}/{len(posts)}] {pid} {title[:50]} -> 帖子正文{'1' if body.strip() else '0'} + 评论{len(cs)}")
        time.sleep(1.2)

    with open("out/raw_reddit.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("out/reddit_status.json", "w", encoding="utf-8") as f:
        json.dump({"posts": len(posts), "rows": len(rows)}, f, ensure_ascii=False)
    print(f"\n合计 {len(rows)} 条（含 {len(posts)} 个帖子）")


if __name__ == "__main__":
    main()
