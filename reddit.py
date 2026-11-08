#!/usr/bin/env python3
"""Reddit 采集：搜索《中餐厅9》相关帖子，抓评论。

Reddit 公开 JSON 接口无需登录：
  - /search.json?q=...&sort=relevance&t=year
  - /comments/{post_id}.json?limit=200&depth=2

输出 out/raw_reddit.jsonl，字段与项目内 Comment 模型一致。
"""
from __future__ import annotations

import json
import os
import time

import requests

OUT_DIR = os.environ.get("OUT_DIR", "out")
S = requests.Session()
S.headers.update({"User-Agent": "academic-research-bot/0.1 (cultural communication study)"})

QUERIES = [
    '"Chinese Restaurant" S9',
    '"Chinese Restaurant" Africa MangoTV',
    '"Chinese Restaurant" Ding Yuxi',
    '"中餐厅9"',
    '"中餐厅" 摩洛哥',
    '"The Chinese Restaurant" variety Morocco',
    '"Chinese Restaurant" season 9 cdrama',
    '"Chinese Restaurant" huang xiaoming 2025',
]
MAX_POSTS_PER_QUERY = 50
MAX_COMMENTS_PER_POST = 200


def jget(url: str, params: dict | None = None, tries: int = 3) -> dict | list | None:
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(5 + i * 5)
                continue
            print(f"  HTTP {r.status_code} {url[:80]}")
            return None
        except Exception as e:
            print(f"  err {str(e)[:70]}")
            time.sleep(2)
    return None


def search_posts(q: str) -> list[dict]:
    out = []
    d = jget("https://www.reddit.com/search.json",
             {"q": q, "sort": "relevance", "t": "year", "limit": 100})
    if not d:
        return out
    for ch in d.get("data", {}).get("children", []):
        d0 = ch.get("data", {})
        out.append({
            "id": d0.get("id"),
            "title": d0.get("title") or "",
            "selftext": (d0.get("selftext") or "")[:2000],
            "subreddit": d0.get("subreddit_name_prefixed") or "",
            "score": d0.get("score") or 0,
            "num_comments": d0.get("num_comments") or 0,
            "created_utc": d0.get("created_utc") or 0,
            "url": d0.get("url") or "",
            "permalink": d0.get("permalink") or "",
        })
    return out


def flatten(children: list, out: list, depth: int = 0):
    for ch in children or []:
        if ch.get("kind") != "t1":
            continue
        d = ch.get("data", {})
        body = (d.get("body") or "").strip()
        if body and body not in ("[removed]", "[deleted]"):
            out.append({
                "cid": d.get("id") or "",
                "text": body,
                "like": d.get("score") or 0,
                "user": d.get("author") or "",
                "depth": depth,
                "parent": d.get("parent_id") or "",
                "created_utc": d.get("created_utc") or 0,
                "awards": d.get("total_awards_received") or 0,
            })
        replies = (d.get("replies") or {}).get("data", {}).get("children", [])
        if replies and depth < 1:
            flatten(replies, out, depth + 1)


def fetch_comments(post_id: str) -> list[dict]:
    d = jget(f"https://www.reddit.com/comments/{post_id}.json",
             {"limit": MAX_COMMENTS_PER_POST, "depth": 2, "sort": "top"})
    if not isinstance(d, list) or len(d) < 2:
        return []
    out: list[dict] = []
    flatten(d[1].get("data", {}).get("children", []), out)
    return out


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    posts: dict[str, dict] = {}
    for q in QUERIES:
        ps = search_posts(q)
        print(f"[search] {q} -> {len(ps)}")
        for p in ps:
            posts.setdefault(p["id"], p)
        time.sleep(2)

    # 只保留有讨论量的
    posts = {k: v for k, v in posts.items() if v["num_comments"] >= 3}
    print(f"\n候选帖子 {len(posts)} 条")
    for p in sorted(posts.values(), key=lambda x: -x["num_comments"])[:20]:
        print(f"  r/{p['subreddit'][2:]:<22} c={p['num_comments']:<4} {p['title'][:70]}")

    rows: list[dict] = []
    for i, (pid, p) in enumerate(sorted(posts.items(), key=lambda kv: -kv[1]["num_comments"]), 1):
        print(f"\n[{i}/{len(posts)}] {pid} {p['title'][:60]}")
        cs = fetch_comments(pid)
        print(f"  => {len(cs)} 条评论")
        for c in cs:
            rows.append({
                "platform": "Reddit",
                "platform_region": "海外",
                "video_id": pid,
                "video_title": f"[{p['subreddit']}] {p['title']}",
                "cid": c["cid"],
                "publish_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(c["created_utc"]))
                if c["created_utc"] else "",
                "user_name": c["user"],
                "user_region": "",
                "text": c["text"],
                "like": c["like"],
                "reply_count": 0,
                "parent_cid": c["parent"],
                "raw": {"depth": c["depth"], "post_score": p["score"],
                        "post_comments": p["num_comments"], "subreddit": p["subreddit"],
                        "post_url": "https://www.reddit.com" + p["permalink"]},
            })
        with open(os.path.join(OUT_DIR, "raw_reddit.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        time.sleep(1.5)

    print(f"\n合计 {len(rows)} 条评论 / {len(posts)} 条帖子")
    with open(os.path.join(OUT_DIR, "reddit_posts.json"), "w", encoding="utf-8") as f:
        json.dump(list(posts.values()), f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
