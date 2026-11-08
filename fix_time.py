#!/usr/bin/env python3
"""修复英文版数据集的发布时间：部分 Invidious 实例返回的 published 是常数。

做法：
  1. 各实例取同一视频首页评论，比较 published 的取值多样性，选出时间戳可信的
  2. 用可信实例重新翻页，建立 cid -> 真实时间
  3. 回填 out/raw_eng.jsonl 的 publish_time
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

import yt_instances as yi

OUT_DIR = os.environ.get("OUT_DIR", "out")
RAW = os.path.join(OUT_DIR, "raw_eng.jsonl")
PROBE_VID = "MU0qexL9obc"


def iso(ts: int) -> str:
    return dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def page(base: str, vid: str, cont: str | None = None) -> dict:
    try:
        params = {"continuation": cont} if cont else {}
        r = yi.S.get(f"{base}/api/v1/comments/{vid}", params=params, timeout=25)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def main():
    yi.VIDEO_ID = PROBE_VID
    ok = yi.probe_all(yi.discover())
    cands = [g["base"] for g in ok]
    print("实例", len(cands))

    best, best_score = None, -1
    for base in cands:
        d = page(base, PROBE_VID)
        cs = d.get("comments") or []
        ts = [c.get("published") for c in cs if isinstance(c.get("published"), int)]
        if not ts:
            print(f"  {base}: 无 published")
            continue
        uniq = len(set(ts))
        span = max(ts) - min(ts)
        years = {dt.datetime.utcfromtimestamp(t).year for t in ts}
        print(f"  {base}: n={len(ts)} 唯一值={uniq} 跨度={span//86400}天 年份={sorted(years)}")
        score = uniq * 1000 + min(span // 86400, 900)
        if uniq > 1 and score > best_score:
            best, best_score = base, score

    if not best:
        print("没有实例返回可信时间戳，保留相对时间文本")
        return 1
    print("选用", best)

    rows = [json.loads(l) for l in open(RAW, encoding="utf-8") if l.strip()]
    vids = sorted({r["video_id"] for r in rows})
    tmap: dict[str, str] = {}
    relmap: dict[str, str] = {}
    for vid in vids:
        d = page(best, vid)
        cont = d.get("continuation")
        p = 0
        while True:
            p += 1
            cs = d.get("comments") or []
            for c in cs:
                cid = c.get("commentId")
                ts = c.get("published")
                if cid and isinstance(ts, int):
                    tmap[cid] = iso(ts)
                if cid and c.get("publishedText"):
                    relmap[cid] = c["publishedText"]
            print(f"  {vid} p{p} 累计时间戳 {len(tmap)}")
            if not cont or p > 40:
                break
            d = page(best, vid, cont)
            cont = d.get("continuation")
            if not (d.get("comments") or []):
                break
            time.sleep(0.5)

    hit = 0
    for r in rows:
        if r["cid"] in tmap:
            r["publish_time"] = tmap[r["cid"]]
            hit += 1
        elif r["cid"] in relmap:
            r["publish_time"] = relmap[r["cid"]]
    print(f"回填 {hit}/{len(rows)} 条")

    with open(RAW, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    spans = sorted(r["publish_time"][:10] for r in rows)
    print("时间范围", spans[0], "→", spans[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
