#!/usr/bin/env python3
"""Reddit 采集（走 Arctic Shift 归档库，绕过 Reddit 官方 403）。

端点（免认证）：
  /api/posts/search?subreddit=...&query=...&after=...&limit=auto
  /api/comments/tree?link_id=t3_<post_id>&limit=25000   ← 整棵评论树

注意：keyword 参数必须和 subreddit 一起用；limit 最大 100（auto 可到 1000）。
"""
from __future__ import annotations

import json
import os
import time

import requests

OUT_DIR = os.environ.get("OUT_DIR", "out")
BASE = "https://arctic-shift.photon-reddit.com/api"
S = requests.Session()
S.headers.update({"User-Agent": "cultural-research/1.0"})

# 目标版块 × 搜索词
TASKS = [
    ("cdrama", "Chinese Restaurant"),
    ("cdrama", "Chinese Restaurant S9"),
    ("cdramafans", "Chinese Restaurant"),
    ("ChineseDrama", "Chinese Restaurant"),
    ("cdtv", "Chinese Restaurant"),
    ("morocco", "Chinese Restaurant"),
    ("tangier", "中餐厅"),
    ("morocco", "中餐厅"),
    ("cdrama", "Ding Yuxi restaurant"),
    ("cdrama", "Huang Xiaoming restaurant"),
    ("ChineseFood", "Chinese Restaurant show"),
]
AFTER = "2025-05-01"          # 节目 2025 年 5 月开播
MIN_COMMENTS = 3              # 帖子至少 3 条评论才抓
KEEP_TERMS = ["restaurant", "s9", "season 9", "africa", "morocco", "tangier",
              "中餐厅", "中餐廳", "ding yuxi", "huang xiaoming", "mangotv"]


def jget(url: str, params: dict, tries: int = 3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 422:
                time.sleep(3 + i * 4)
                continue
            print(f"    HTTP {r.status_code} {str(params)[:90]}")
            return None
        except Exception as e:
            print(f"    err {str(e)[:70]}")
            time.sleep(2)
    return None


def search_posts(sub: str, query: str) -> list[dict]:
    """分页抓全部匹配帖子。"""
    out, after = [], AFTER
    while True:
        d = jget(f"{BASE}/posts/search",
                 {"subreddit": sub, "query": query, "after": after,
                  "limit": "auto", "sort": "asc",
                  "fields": "id,title,selftext,subreddit,score,num_comments,created_utc,permalink"})
        rows = (d or {}).get("data") or []
        if not rows:
            break
        out += rows
        if len(rows) < 100:
            break
        after = rows[-1]["created_utc"] + 1
        time.sleep(0.8)
    return out


def comment_tree(post_id: str) -> list[dict]:
    d = jget(f"{BASE}/comments/tree", {"link_id": f"t3_{post_id}", "limit": 25000,
                                       "start_depth": 6, "start_breadth": 6})
    return (d or {}).get("data") or []


def flatten(nodes: list, out: list, depth: int = 0):
    for nd in nodes or []:
        if nd.get("kind") != "t1":
            continue
        d = nd.get("data", {})
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
            })
        flatten(d.get("children") or [], out, depth + 1)


def relevant(p: dict) -> bool:
    t = (p.get("title", "") + " " + (p.get("selftext") or "")[:400]).lower()
    return any(k in t for k in KEEP_TERMS)


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    posts: dict[str, dict] = {}
    for sub, q in TASKS:
        ps = search_posts(sub, q)
        keep = [p for p in ps if relevant(p) and (p.get("num_comments") or 0) >= MIN_COMMENTS]
        print(f"[search] r/{sub:<14} q={q:<26} -> {len(ps):>3} 帖, 保留 {len(keep)}")
        for p in keep:
            posts.setdefault(p["id"], p)
        time.sleep(0.6)

    print(f"\n候选帖子 {len(posts)} 条")
    for p in sorted(posts.values(), key=lambda x: -(x.get("num_comments") or 0))[:20]:
        print(f"  r/{p['subreddit']:<16} c={p.get('num_comments'):<4} {p['title'][:70]}")

    rows: list[dict] = []
    plist = sorted(posts.items(), key=lambda kv: -(kv[1].get("num_comments") or 0))
    for i, (pid, p) in enumerate(plist, 1):
        print(f"\n[{i}/{len(plist)}] {pid} {p['title'][:60]}")
        cs = flatten(comment_tree(pid), [])
        print(f"  => {len(cs)} 条评论")
        for c in cs:
            rows.append({
                "platform": "Reddit",
                "platform_region": "海外",
                "video_id": pid,
                "video_title": f"[r/{p['subreddit']}] {p['title']}",
                "cid": c["cid"],
                "publish_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(c["created_utc"]))
                if c["created_utc"] else "",
                "user_name": c["user"],
                "user_region": "",
                "text": c["text"],
                "like": c["like"],
                "reply_count": 0,
                "parent_cid": c["parent"],
                "raw": {"depth": c["depth"], "post_score": p.get("score"),
                        "post_comments": p.get("num_comments"),
                        "subreddit": "r/" + p["subreddit"],
                        "post_url": "https://www.reddit.com" + (p.get("permalink") or "")},
            })
        with open(os.path.join(OUT_DIR, "raw_reddit.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        time.sleep(0.8)

    print(f"\n合计 {len(rows)} 条评论 / {len(posts)} 条帖子")
    with open(os.path.join(OUT_DIR, "reddit_posts.json"), "w", encoding="utf-8") as f:
        json.dump(list(posts.values()), f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
