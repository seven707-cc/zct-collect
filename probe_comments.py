#!/usr/bin/env python3
"""探测：在 runner 上找出能成功抓取 YouTube 评论的客户端配置组合。

逐个尝试 yt-dlp 的 --extractor-args 组合，输出每条的成功/失败与错误原因。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time

VIDEO = os.environ.get("PROBE_VIDEO", "oRhkf2hNcdQ")
MAXC = os.environ.get("PROBE_MAX", "20")

# 组合：(标签, extractor-args)
COMBOS = [
    ("default",          None),
    ("web_safari",       "player_client=web_safari"),
    ("android",          "player_client=android"),
    ("ios",              "player_client=ios"),
    ("tv",               "player_client=tv"),
    ("mweb",             "player_client=mweb"),
    ("web_embedded",     "player_client=web_embedded"),
    ("android_vr",       "player_client=android_vr"),
    ("tv_simply",        "player_client=tv_simply"),
    ("skip_webpage",     "player_skip=webpage,configs"),
    ("sort_new_nojson",  "comment_sort=new"),
]


def attempt(label: str, ea: str | None) -> dict:
    tmp = tempfile.mkdtemp()
    args = [
        "yt-dlp", "--no-warnings", "--skip-download", "--write-comments",
        "--write-info-json", "--no-write-subs", "--no-write-auto-subs",
        "--no-write-thumbnail", "--no-playlist",
        "--socket-timeout", "25", "--retries", "1",
        "--extractor-args",
        (f"youtube:max_comments={MAXC},all,all,all" + (f";{ea}" if ea else "")),
        "-o", os.path.join(tmp, "%(id)s"),
        f"https://www.youtube.com/watch?v={VIDEO}",
    ]
    t0 = time.time()
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=420)
    except subprocess.TimeoutExpired:
        return {"label": label, "ok": False, "err": "TIMEOUT"}
    dt = round(time.time() - t0, 1)

    info_path = os.path.join(tmp, f"{VIDEO}.info.json")
    n = 0
    title = ""
    if os.path.exists(info_path):
        try:
            with open(info_path, encoding="utf-8") as f:
                info = json.load(f)
            title = (info.get("title") or "")[:40]
            n = len(info.get("comments") or [])
        except Exception:
            pass

    err = ""
    if p.returncode != 0:
        lines = (p.stderr or "").strip().splitlines()
        err = " | ".join(lines[-2:])[:220]
    return {"label": label, "ok": n > 0, "comments": n, "sec": dt,
            "title": title, "err": err}


def main() -> None:
    print(f"探测视频 {VIDEO}，每组合最多 {MAXC} 条评论", flush=True)
    print("=" * 78, flush=True)
    results = []
    for label, ea in COMBOS:
        r = attempt(label, ea)
        results.append(r)
        flag = "OK " if r["ok"] else "FAIL"
        print(f"[{flag}] {label:<16} comments={r.get('comments',0):<4} {r.get('sec')}s  {r.get('err','')[:120]}", flush=True)
        if r["ok"]:
            print(f"       -> 标题: {r.get('title')}", flush=True)
            break
        time.sleep(2)
    print("=" * 78, flush=True)
    ok = [r for r in results if r["ok"]]
    if ok:
        print("可用配置:", ok[0]["label"])
    else:
        print("全部失败：本 runner 出口 IP 被完全拦截，需换 IP 或加 cookies")
    with open("probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
