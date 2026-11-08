#!/usr/bin/env python3
"""诊断：英文版视频到底有没有评论，还是实例拿不到。"""
import json
import os
import time

import yt_instances as yi

IDS = os.environ.get("IDS", "").split(",") or [
    "MU0qexL9obc", "MYRHo-E79iw", "DdatAHPrCzQ", "NCDdX40qwZg", "tWlL8G8EOu4",
    "lJtttygX7D0", "XpjPAWu522E", "wGDus41Zqlo", "eZNmawxqg9Y", "2UIP3nZ0hkU",
    "GE2KqInXXgY", "JYT37xL8xRw", "Jyu-4V_e0qQ", "KZoXMNwSU88",
]

yi.VIDEO_ID = "MU0qexL9obc"
ok = yi.probe_all(yi.discover())
good = sorted(ok, key=lambda x: -x["n"])[:5]
print("instances:", [g["base"] for g in good])

for vid in IDS:
    print(f"\n=== {vid} ===")
    for g in good:
        base, kind = g["base"], g["kind"]
        try:
            if kind == "invidious":
                r = yi.S.get(f"{base}/api/v1/videos/{vid}", timeout=20)
                meta = r.json() if r.status_code == 200 else {}
                r2 = yi.S.get(f"{base}/api/v1/comments/{vid}", timeout=20)
                d2 = r2.json() if r2.status_code == 200 else {}
                print(f"  [{base}] meta={r.status_code} title={str(meta.get('title'))[:50]!r} "
                      f"cc={meta.get('commentCount')} subs={meta.get('subCount')} "
                      f"| comments={r2.status_code} n={len(d2.get('comments') or [])} "
                      f"err={str(d2.get('error'))[:40]}")
            else:
                r = yi.S.get(f"{base}/streams/{vid}", timeout=20)
                meta = r.json() if r.status_code == 200 else {}
                r2 = yi.S.get(f"{base}/comments/{vid}", timeout=20)
                d2 = r2.json() if r2.status_code == 200 else {}
                print(f"  [{base}] meta={r.status_code} title={str(meta.get('title'))[:50]!r} "
                      f"cc={meta.get('commentCount')} | comments={r2.status_code} "
                      f"n={len(d2.get('comments') or [])} err={str(d2.get('error'))[:40]}")
        except Exception as e:
            print(f"  [{base}] ERR {str(e)[:60]}")
        time.sleep(0.5)
