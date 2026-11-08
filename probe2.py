#!/usr/bin/env python3
"""第二轮平台探测：找 YouTube 之外、能真正拿到《中餐厅9》讨论的海外平台。

输出 out/probe2.json，含每个平台的命中数量与前几条样本。
"""
from __future__ import annotations

import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}


def bsky():
    out = []
    for q in ["中餐厅", "中餐厅9", "Chinese Restaurant MangoTV", "丁禹兮", "Morocco Chinese restaurant"]:
        try:
            r = S.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                      params={"q": q, "limit": 50}, timeout=25)
            d = r.json() if r.status_code == 200 else {}
            posts = d.get("posts", [])
            print(f"[bsky] {q}: {r.status_code} posts={len(posts)}")
            for p in posts[:5]:
                print("   -", p["author"]["handle"], "|",
                      p["record"].get("text", "")[:70].replace("\n", " "))
            out.append({"q": q, "status": r.status_code,
                        "posts": [{"uri": p["uri"], "text": p["record"].get("text", ""),
                                   "author": p["author"]["handle"],
                                   "reply": p.get("replyCount", 0),
                                   "like": p.get("likeCount", 0)} for p in posts]})
        except Exception as e:
            print(f"[bsky] {q} ERR {str(e)[:80]}")
            out.append({"q": q, "err": str(e)[:100]})
    RES["bluesky"] = out


def dailymotion():
    out = {}
    for q in ["中餐厅", "Chinese Restaurant MangoTV", "Ding Yuxi"]:
        try:
            r = S.get("https://api.dailymotion.com/videos",
                      params={"search": q, "limit": 10,
                              "fields": "id,title,url,created_time,views_total,owner"}, timeout=25)
            d = r.json() if r.status_code == 200 else {}
            print(f"[dm] {q}: {r.status_code} total={d.get('total')} n={len(d.get('list', []))}")
            for v in d.get("list", [])[:5]:
                print("   -", v.get("id"), str(v.get("title"))[:60])
            out[q] = {"total": d.get("total"), "list": d.get("list", [])}
        except Exception as e:
            print(f"[dm] {q} ERR {str(e)[:80]}")
            out[q] = {"err": str(e)[:100]}
    # 单条视频页是否带评论
    vids = [v["id"] for v in out.get("中餐厅", {}).get("list", [])[:3] if v.get("id")]
    for vid in vids:
        try:
            r = S.get(f"https://www.dailymotion.com/video/{vid}", timeout=25)
            txt = r.text
            ncmt = len(re.findall(r"comment", txt, re.I))
            print(f"[dm] page {vid}: {r.status_code} len={len(txt)} 'comment'={ncmt}")
            out.setdefault("pages", {})[vid] = {"status": r.status_code, "comment_kw": ncmt}
        except Exception as e:
            print(f"[dm] page {vid} ERR {str(e)[:60]}")
    RES["dailymotion"] = out


def mdl():
    out = {}
    for url in ["https://mydramalist.com/786938-chinese-restaurant-season-9/reviews",
                "https://mydramalist.com/786938-chinese-restaurant-season-9"]:
        try:
            r = S.get(url, timeout=25)
            t = r.text
            blocks = re.findall(r'<div class="review-body">(.*?)</div>', t, re.S)
            print(f"[mdl] {url[-30:]}: {r.status_code} len={len(t)} review_blocks={len(blocks)}")
            out[url] = {"status": r.status_code, "len": len(t),
                        "review_blocks": len(blocks),
                        "comment_count_hint": re.findall(r'comments-alt"></i>\s*(\d+)', t)[:5]}
            if blocks:
                print("   sample:", re.sub(r"<[^>]+>", "", blocks[0])[:200].replace("\n", " "))
        except Exception as e:
            print(f"[mdl] ERR {str(e)[:80]}")
            out[url] = {"err": str(e)[:100]}
    RES["mdl"] = out


def mastodon():
    out = {}
    for host in ["https://mastodon.social", "https://mstdn.social"]:
        for tag in ["中餐厅", "ChineseRestaurant"]:
            try:
                r = S.get(f"{host}/api/v1/timelines/tag/{tag}", params={"limit": 20}, timeout=20)
                n = len(r.json()) if r.status_code == 200 else 0
                print(f"[masto] {host} #{tag}: {r.status_code} n={n}")
                out[f"{host}#{tag}"] = {"status": r.status_code, "n": n}
            except Exception as e:
                print(f"[masto] {host}#{tag} ERR {str(e)[:60]}")
    RES["mastodon"] = out


def main():
    bsky()
    dailymotion()
    mdl()
    mastodon()
    with open("out/probe2.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
