#!/usr/bin/env python3
"""补齐英文版剩余剧集：在已有 raw_eng.jsonl 基础上增量采集。"""
from __future__ import annotations

import json
import os
import re
import time

import yt_instances as yi

OUT_DIR = os.environ.get("OUT_DIR", "out")
RAW = os.path.join(OUT_DIR, "raw_eng.jsonl")
ENG_RE = re.compile(r"\[ENG\]", re.I)
EXTRA = [x.strip() for x in os.environ.get("IDS", "").split(",") if x.strip()]
MISSING_EP = [int(x) for x in os.environ.get("MISSING_EP", "").split(",") if x.strip()]


def search(base, q):
    try:
        r = yi.S.get(f"{base}/api/v1/search", params={"q": q, "type": "video"}, timeout=20)
        if r.status_code == 200:
            return [{"id": it.get("videoId"), "title": it.get("title") or ""}
                    for it in r.json() or [] if it.get("type") == "video"]
    except Exception:
        pass
    return []


def fetch(kind, base, vid):
    rows, cont = {}, None
    for page in range(1, 40):
        try:
            params = {"continuation": cont} if cont else {}
            if kind == "invidious":
                r = yi.S.get(f"{base}/api/v1/comments/{vid}", params=params, timeout=25)
            else:
                r = (yi.S.get(f"{base}/nextpage/comments/{vid}", params={"nextpage": cont}, timeout=25)
                     if cont else yi.S.get(f"{base}/comments/{vid}", timeout=25))
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
            if row["text"] and row["cid"] not in rows:
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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    existing = []
    if os.path.exists(RAW):
        existing = [json.loads(l) for l in open(RAW, encoding="utf-8") if l.strip()]
    have = {r["video_id"] for r in existing}
    titled = {r["video_id"]: r.get("video_title", "") for r in existing}
    print("已有", len(existing), "条 /", len(have), "条视频")

    yi.VIDEO_ID = "MU0qexL9obc"
    ok = yi.probe_all(yi.discover())
    good = sorted(ok, key=lambda x: -x["n"])[:5]
    print("instances", [g["base"] for g in good])

    cands: dict[str, str] = {}
    for vid in EXTRA:
        cands[vid] = ""
    for ep in MISSING_EP:
        for g in good[:2]:
            for q in (f"[ENG] EP{ep:02d} The Chinese Restaurant",
                      f"The Chinese Restaurant S9 EP{ep:02d} English"):
                for v in search(g["base"], q):
                    if v["id"] and ENG_RE.search(v["title"] or "") and f"EP{ep:02d}" in v["title"].upper().replace(" ", ""):
                        cands.setdefault(v["id"], v["title"])
    print("新增候选", cands)

    new_rows = []
    for vid, title in cands.items():
        if vid in have and title in ("", titled.get(vid, "")):
            print("跳过（已抓过）", vid)
            continue
        print(f"\n{vid} {title[:70]}")
        rows = []
        for g in good:
            got = fetch(g["kind"], g["base"], vid)
            if len(got) > len(rows):
                rows = got
            if len(rows) >= 150:
                break
        print(f"  => {len(rows)} 条")
        if not rows:
            continue
        if not title:
            title = "".join(ch for ch in rows[0].get("video_title") or "" if True) or ""
        for r in rows:
            r["video_title"] = title or r.get("video_title", "")
        new_rows += rows

    all_rows = [r for r in existing if r["video_id"] not in {x["video_id"] for x in new_rows}]
    all_rows += new_rows
    with open(RAW, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n最终 {len(all_rows)} 条 / {len({r['video_id'] for r in all_rows})} 条视频")


if __name__ == "__main__":
    main()
