#!/usr/bin/env python3
"""深挖英文版视频清单：频道完整视频列表 + 相关播放列表 + 多查询搜索。"""
from __future__ import annotations

import json
import os
import re
import time

import yt_instances as yi

OUT_DIR = os.environ.get("OUT_DIR", "out")
SEED = "MU0qexL9obc"
ENG_RE = re.compile(r"\[ENG\]|ENG\s*SUB", re.I)
EP_RE = re.compile(r"EP\s*0?(\d{1,2})", re.I)


def jget(url, params=None, tries=1):
    for _ in range(tries):
        try:
            r = yi.S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(0.5)
    return {}


def all_channel_videos(base, cid, maxpage=12):
    out = []
    url = f"{base}/api/v1/channels/{cid}/videos"
    d = jget(url)
    for v in d.get("videos", []):
        out.append({"id": v.get("videoId"), "title": v.get("title") or ""})
    cont = d.get("continuation")
    p = 0
    while cont and p < maxpage:
        p += 1
        d = jget(url, {"continuation": cont})
        for v in d.get("videos", []):
            out.append({"id": v.get("videoId"), "title": v.get("title") or ""})
        cont = d.get("continuation")
        time.sleep(0.4)
    return out


def channel_playlists(base, cid, maxpage=6):
    out = []
    url = f"{base}/api/v1/channels/{cid}/playlists"
    d = jget(url)
    for pl in d.get("playlists", []):
        out.append({"id": pl.get("playlistId"), "title": pl.get("title") or "",
                    "n": pl.get("videoCount")})
    cont = d.get("continuation")
    p = 0
    while cont and p < maxpage:
        p += 1
        d = jget(url, {"continuation": cont})
        for pl in d.get("playlists", []):
            out.append({"id": pl.get("playlistId"), "title": pl.get("title") or "",
                        "n": pl.get("videoCount")})
        cont = d.get("continuation")
        time.sleep(0.4)
    return out


def playlist_videos(base, plid):
    d = jget(f"{base}/api/v1/playlists/{plid}")
    out = []
    for v in d.get("videos", []) or []:
        out.append({"id": v.get("videoId"), "title": v.get("title") or ""})
    return out


def search(base, q):
    d = jget(f"{base}/api/v1/search", {"q": q, "type": "video"})
    return [{"id": it.get("videoId"), "title": it.get("title") or ""}
            for it in (d or []) if it.get("type") == "video"]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    yi.VIDEO_ID = SEED
    ok = yi.probe_all(yi.discover())
    good = [g["base"] for g in sorted(ok, key=lambda x: -x["n"])[:4]]
    base = good[0]
    print("bases", good)

    meta = jget(f"{base}/api/v1/videos/{SEED}")
    cid = meta.get("authorId")
    print("channel", cid, meta.get("author"))

    dump = {"channel": cid, "videos": [], "playlists": [], "search": []}
    if cid:
        vs = all_channel_videos(base, cid)
        print("频道视频", len(vs))
        dump["videos"] = vs
        pls = channel_playlists(base, cid)
        print("播放列表", len(pls))
        dump["playlists"] = pls
        hit = [p for p in pls if "chinese restaurant" in p["title"].lower()
               or "中餐厅" in p["title"] or "中餐廳" in p["title"]]
        print("相关播放列表", [(p["title"][:40], p["n"]) for p in hit])
        pvids = []
        for p in hit[:6]:
            vids = playlist_videos(base, p["id"])
            print(f"  {p['title'][:40]} -> {len(vids)}")
            pvids += vids
        dump["playlist_videos"] = pvids

    queries = []
    for i in range(1, 14):
        queries += [f"The Chinese Restaurant S9 EP{i:02d} English",
                    f"中餐厅9 英文版 EP{i:02d}"]
    queries += ["The Chinese Restaurant S9 full episode english subtitles",
                "Chinese Restaurant Africa Season english"]
    seen_q = []
    for q in queries:
        for b in good[:2]:
            res = search(b, q)
            if res:
                dump["search"] += res
                seen_q.append(q)
                break
    print("搜索命中累计", len(dump["search"]))

    json.dump(dump, open(os.path.join(OUT_DIR, "chan_dump.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 汇总英文候选
    cand = {}
    for src in ("videos", "playlist_videos", "search"):
        for v in dump.get(src) or []:
            vid, t = v.get("id"), v.get("title") or ""
            if vid and ENG_RE.search(t):
                cand.setdefault(vid, {"id": vid, "title": t})
    print("\n[ENG] 候选", len(cand))
    for k, v in cand.items():
        print(" ", k, v["title"][:80])
    json.dump(list(cand.values()), open(os.path.join(OUT_DIR, "eng_candidates.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
