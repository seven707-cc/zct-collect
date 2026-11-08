#!/usr/bin/env python3
"""第三轮：Reddit 归档 API（arctic-shift）+ Dailymotion 评论探测。"""
from __future__ import annotations

import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}
AS = "https://arctic-shift.photon-reddit.com/api"


def try_get(url, params, tag):
    try:
        r = S.get(url, params=params, timeout=30)
        print(f"[{tag}] {r.status_code} {url.split('/api')[-1][:60]} len={len(r.content)}")
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                print("   not json:", r.text[:150].replace("\n", " "))
        else:
            print("   ", r.text[:150].replace("\n", " "))
    except Exception as e:
        print(f"[{tag}] ERR {str(e)[:80]}")
    return None


def reddit_archive():
    out = {}
    # 1) 全站搜「中餐厅」
    for q in ["中餐厅", "Chinese Restaurant S9", "中餐厅9"]:
        d = try_get(f"{AS}/posts/search", {"query": q, "limit": 100, "sort": "desc"}, "arctic-posts")
        posts = (d or {}).get("data") or []
        print(f"   query={q} posts={len(posts)}")
        for p in posts[:5]:
            print("     -", p.get("subreddit"), "|", str(p.get("title"))[:70])
        out[f"posts::{q}"] = {"n": len(posts),
                              "items": [{"id": p.get("id"), "subreddit": p.get("subreddit"),
                                         "title": p.get("title"), "num_comments": p.get("num_comments"),
                                         "created_utc": p.get("created_utc"),
                                         "selftext": (p.get("selftext") or "")[:300]} for p in posts]}
    # 2) 按子版搜
    for sub in ["CDrama", "ChineseTV", "Cantonese", "asiandrama"]:
        d = try_get(f"{AS}/posts/search", {"subreddit": sub, "query": "Chinese Restaurant",
                                          "limit": 100}, "arctic-sub")
        posts = (d or {}).get("data") or []
        print(f"   r/{sub} posts={len(posts)}")
        out[f"sub::{sub}"] = {"n": len(posts),
                              "items": [{"id": p.get("id"), "title": p.get("title"),
                                         "num_comments": p.get("num_comments")} for p in posts]}
    RES["reddit"] = out


def dailymotion_comments():
    out = {}
    vids = ["x8nnzxc", "x9pv088", "x9pbhsy"]
    for vid in vids:
        d = try_get(f"https://api.dailymotion.com/video/{vid}/comments", {"limit": 20}, "dm-comments")
        if d:
            out[vid] = d
    # 页面里找评论区块
    for vid in vids[:2]:
        try:
            r = S.get(f"https://www.dailymotion.com/video/{vid}", timeout=25)
            t = r.text
            has = re.findall(r'(comment[_-]?(?:list|item|body)|data-testid="comment)', t, re.I)
            print(f"[dm-page] {vid} {r.status_code} comment_markers={len(has)}")
            if has:
                i = t.lower().find("comment")
                print("   sample:", re.sub(r"<[^>]+>", " ", t[i:i + 300])[:200])
            out.setdefault("pages", {})[vid] = {"status": r.status_code, "markers": len(has)}
        except Exception as e:
            print(f"[dm-page] {vid} ERR {str(e)[:60]}")
    RES["dailymotion"] = out


def main():
    reddit_archive()
    dailymotion_comments()
    with open("out/probe3.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
