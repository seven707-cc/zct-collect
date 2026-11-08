#!/usr/bin/env python3
"""专抓《中餐厅9》英文频道版本（MangoTV English / The Chinese Restaurant S9）。

流程：
  1. 探测可用 Invidious / Piped 实例（复用 yt_instances 的逻辑）
  2. 用实例的搜索接口找 EP00~EP13 的英文版视频（标题不含中文字符、含 Chinese Restaurant）
  3. 合并内置已知 ID，逐条视频翻页抓全量评论
  4. 输出 out/raw_yt_eng.jsonl 与 out/eng_videos.json
"""
from __future__ import annotations

import json
import os
import re
import time

import yt_instances as yi

OUT_DIR = os.environ.get("OUT_DIR", "out")
MAX_PER_VIDEO = int(os.environ.get("MAX_COMMENTS", "0") or 0)

KNOWN = [
    "lJtttygX7D0", "JYT37xL8xRw",                       # Prologue / EP00
    "MU0qexL9obc", "XpjPAWu522E", "wGDus41Zqlo",        # EP01
    "MYRHo-E79iw",                                      # EP02
    "DdatAHPrCzQ", "yRcoEwpnL24",                       # EP03
    "NCDdX40qwZg", "KZoXMNwSU88",                       # EP04 / Premiere
    "M-6yA-3iMOw", "v8CJKCKxX4Q", "OQM4J0sqb7E",        # 片段 EP4/EP5
    "eZNmawxqg9Y",                                      # Bonus EP05
    "tWlL8G8EOu4",                                      # EP06
    "2UIP3nZ0hkU",                                      # Partner Diaries EP07
    "GE2KqInXXgY",                                      # Partner Diary EP08
]

CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
EPRE = re.compile(r"(?:EP|Episode|Tập)\s*0?(\d{1,2})", re.I)


def search(kind: str, base: str, q: str, pages: int = 2) -> list[dict]:
    out: list[dict] = []
    for p in range(1, pages + 1):
        try:
            if kind == "invidious":
                r = yi.S.get(f"{base}/api/v1/search",
                             params={"q": q, "type": "video", "page": p}, timeout=20)
                if r.status_code != 200:
                    return out
                for it in r.json() or []:
                    if it.get("type") != "video":
                        continue
                    out.append({"id": it.get("videoId"), "title": it.get("title") or "",
                                "author": it.get("author") or ""})
            else:
                r = yi.S.get(f"{base}/search",
                             params={"q": q, "filter": "videos"}, timeout=20)
                if r.status_code != 200:
                    return out
                for it in (r.json() or {}).get("items", []):
                    url = it.get("url") or ""
                    vid = url.split("v=")[-1] if "v=" in url else url.strip("/").split("/")[-1]
                    out.append({"id": vid, "title": it.get("title") or "",
                                "author": it.get("uploaderName") or ""})
        except Exception as e:
            print(f"  [search] {base} p{p} err {str(e)[:60]}")
            return out
        time.sleep(0.4)
    return out


def is_eng(title: str) -> bool:
    if not title or CJK.search(title):
        return False
    t = title.lower()
    return "chinese restaurant" in t


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    yi.VIDEO_ID = "MU0qexL9obc"
    items = yi.discover()
    print(f"[probe] 待测实例 {len(items)} 个")
    ok = yi.probe_all(items)
    if not ok:
        print("没有可用实例")
        return 1
    good = sorted(ok, key=lambda x: -x["n"])[:6]
    print(f"[probe] 可用 {len(ok)}，选用 {[g['base'] for g in good]}")

    queries = []
    for i in range(0, 14):
        queries.append(f"The Chinese Restaurant Africa Season EP{i:02d}")
    queries += [
        "Chinese Restaurant African Startup Season EP07",
        "Chinese Restaurant African Startup Season EP08",
        "Chinese Restaurant African Startup Season EP09",
        "Chinese Restaurant African Startup Season EP10",
        "Chinese Restaurant African Startup Season EP11",
        "Chinese Restaurant African Startup Season EP12",
        "Chinese Restaurant African Venture Season full episode",
        "Chinese Restaurant Africa Entrepreneurship Season full episode",
    ]

    found: dict[str, dict] = {}
    for q in queries:
        got = None
        for cand in good[:3]:
            res = search(cand["kind"], cand["base"], q)
            if res:
                got = res
                break
        if not got:
            print(f"[search] 无结果: {q}")
            continue
        n0 = len(found)
        for it in got:
            vid, title = it.get("id"), it.get("title", "")
            if not vid or vid in found:
                continue
            if not is_eng(title):
                continue
            m = EPRE.search(title)
            found[vid] = {"id": vid, "title": title, "ep": int(m.group(1)) if m else None,
                          "author": it.get("author", "")}
        print(f"[search] {q} -> +{len(found)-n0}  (累计 {len(found)})")

    for vid in KNOWN:
        found.setdefault(vid, {"id": vid, "title": "", "ep": None, "author": ""})

    vids = list(found.keys())
    print(f"\n[collect] 待抓 {len(vids)} 条视频")
    json.dump(list(found.values()), open(os.path.join(OUT_DIR, "eng_videos.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)

    all_rows: list[dict] = []
    for i, vid in enumerate(vids, 1):
        print(f"\n[{i}/{len(vids)}] {vid} {found[vid]['title'][:70]}")
        rows: list[dict] = []
        for cand in good:
            rows = yi.collect(cand["kind"], cand["base"], vid, MAX_PER_VIDEO)
            if rows:
                print(f"  用 {cand['base']} 拿到 {len(rows)} 条")
                break
            print(f"  {cand['base']} 失败，换实例")
        all_rows += rows
        with open(os.path.join(OUT_DIR, "raw_yt_eng.jsonl"), "w", encoding="utf-8") as f:
            for r in all_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n合计 {len(all_rows)} 条 / {len(vids)} 条视频")
    with open(os.path.join(OUT_DIR, "eng_status.json"), "w", encoding="utf-8") as f:
        json.dump({"videos": len(vids), "comments": len(all_rows),
                   "per_video": {v: sum(1 for r in all_rows if r["video_id"] == v) for v in vids}},
                  f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
