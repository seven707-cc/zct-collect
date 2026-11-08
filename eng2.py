#!/usr/bin/env python3
"""抓《中餐厅9》真正的英文版（[ENG] 系列 / 英文字幕上传）。

要点：
  1. 从 EP01 反查频道，列出频道视频，筛出 [ENG] 系列
  2. 交叉搜索补漏
  3. 多实例 + 多页合并去重，尽量抓满 commentCount
"""
from __future__ import annotations

import json
import os
import re
import time

import yt_instances as yi

OUT_DIR = os.environ.get("OUT_DIR", "out")
SEED = "MU0qexL9obc"
ENG_RE = re.compile(r"\[ENG\]|ENG\s*SUB|English\s*Sub", re.I)


def get_meta(kind: str, base: str, vid: str) -> dict:
    try:
        url = f"{base}/api/v1/videos/{vid}" if kind == "invidious" else f"{base}/streams/{vid}"
        r = yi.S.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def channel_videos(kind: str, base: str, cid: str) -> list[dict]:
    out: list[dict] = []
    try:
        if kind == "invidious":
            url = f"{base}/api/v1/channels/{cid}/videos"
            r = yi.S.get(url, timeout=25)
            if r.status_code != 200:
                return out
            d = r.json()
            for v in d.get("videos", []):
                out.append({"id": v.get("videoId"), "title": v.get("title") or ""})
            cont = d.get("continuation")
            for _ in range(3):
                if not cont:
                    break
                r = yi.S.get(url, params={"continuation": cont}, timeout=25)
                if r.status_code != 200:
                    break
                d = r.json()
                for v in d.get("videos", []):
                    out.append({"id": v.get("videoId"), "title": v.get("title") or ""})
                cont = d.get("continuation")
                time.sleep(0.5)
    except Exception as e:
        print(f"  [channel] err {str(e)[:60]}")
    return out


def search(kind: str, base: str, q: str) -> list[dict]:
    out = []
    try:
        if kind == "invidious":
            r = yi.S.get(f"{base}/api/v1/search", params={"q": q, "type": "video"}, timeout=20)
            if r.status_code == 200:
                for it in r.json() or []:
                    if it.get("type") == "video":
                        out.append({"id": it.get("videoId"), "title": it.get("title") or ""})
        else:
            r = yi.S.get(f"{base}/search", params={"q": q, "filter": "videos"}, timeout=20)
            if r.status_code == 200:
                for it in (r.json() or {}).get("items", []):
                    url = it.get("url") or ""
                    vid = url.split("v=")[-1]
                    out.append({"id": vid, "title": it.get("title") or ""})
    except Exception:
        pass
    return out


def fetch_comments(kind: str, base: str, vid: str) -> list[dict]:
    rows: dict[str, dict] = {}
    cont = None
    for page in range(1, 60):
        try:
            if kind == "invidious":
                params = {"continuation": cont} if cont else {}
                r = yi.S.get(f"{base}/api/v1/comments/{vid}", params=params, timeout=25)
            else:
                if cont:
                    r = yi.S.get(f"{base}/nextpage/comments/{vid}", params={"nextpage": cont}, timeout=25)
                else:
                    r = yi.S.get(f"{base}/comments/{vid}", timeout=25)
            if r.status_code != 200:
                break
            d = r.json()
        except Exception:
            break
        cs = d.get("comments") or []
        if not cs:
            break
        new = 0
        for c in cs:
            row = (yi.norm_invidious(c, vid, "") if kind == "invidious"
                   else yi.norm_piped(c, vid, ""))
            if not row["text"] or row["cid"] in rows:
                continue
            rows[row["cid"]] = row
            new += 1
        print(f"    p{page} +{new} 累计 {len(rows)}")
        if new == 0:
            break
        cont = d.get("continuation") if kind == "invidious" else d.get("nextpage")
        if not cont:
            break
        time.sleep(0.6)
    return list(rows.values())


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    yi.VIDEO_ID = SEED
    ok = yi.probe_all(yi.discover())
    good = sorted(ok, key=lambda x: -x["n"])[:6]
    print("instances:", [g["base"] for g in good])

    # 1) 频道枚举
    meta = {}
    for g in good:
        meta = get_meta(g["kind"], g["base"], SEED)
        if meta.get("authorId"):
            break
    ch = meta.get("authorId")
    print("channel", ch, meta.get("author"))

    cands: dict[str, dict] = {SEED: {"id": SEED, "title": meta.get("title", "[ENG] EP01")}}
    if ch:
        for g in good[:2]:
            vs = channel_videos(g["kind"], g["base"], ch)
            print(f"  频道视频 {len(vs)} 条 ({g['base']})")
            for v in vs:
                if v["id"] and ENG_RE.search(v["title"] or ""):
                    cands[v["id"]] = v
            if len(vs) > 50:
                break

    # 2) 搜索补漏
    queries = ["The Chinese Restaurant S9 [ENG]", "The Chinese Restaurant [ENG] Africa",
               "中餐厅9 英文版", "The Chinese Restaurant Starting Up in Africa English sub"]
    for q in queries:
        for g in good[:2]:
            for v in search(g["kind"], g["base"], q):
                if v["id"] and ENG_RE.search(v["title"] or ""):
                    cands.setdefault(v["id"], v)
        print(f"  search {q} -> 累计 {len(cands)}")

    print(f"\n英文版候选 {len(cands)} 条：")
    for k, v in cands.items():
        print("  ", k, v["title"][:80])

    # 3) 抓评论
    all_rows: list[dict] = []
    for i, (vid, info) in enumerate(cands.items(), 1):
        print(f"\n[{i}/{len(cands)}] {vid} {info['title'][:70]}")
        rows: list[dict] = []
        for g in good:
            got = fetch_comments(g["kind"], g["base"], vid)
            if len(got) > len(rows):
                rows = got
            if len(rows) >= 200:
                break
        for r in rows:
            r["video_title"] = info["title"]
        print(f"  => {len(rows)} 条")
        all_rows += rows
        with open(os.path.join(OUT_DIR, "raw_eng.jsonl"), "w", encoding="utf-8") as f:
            for r in all_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    json.dump({k: v for k, v in cands.items()}, open(os.path.join(OUT_DIR, "eng_videos.json"),
              "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n合计 {len(all_rows)} 条 / {len(cands)} 条视频")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
