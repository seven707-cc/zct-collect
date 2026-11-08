#!/usr/bin/env python3
"""在 GitHub Actions（境外 runner）上采集 YouTube 评论。

不下载任何视频，只取评论。产出 out/ 下三个文件：
    yt_videos.json      发现的视频清单
    raw_youtube.jsonl   评论明细（字段与本地 zct 管线对齐）
    raw_youtube.csv     同上，Excel 可直接打开

环境变量（都由 workflow 注入）：
    QUERIES        搜索关键词，用 | 分隔
    VIDEO_IDS      直接指定视频 ID，用逗号分隔（优先级高于搜索）
    CHANNELS       频道/播放列表 URL，用 | 分隔
    MAX_COMMENTS   每条视频最多抓多少条，0 = 全量
    MAX_VIDEOS     最多处理多少条视频，0 = 不限
    SORT           top / new
    LANG           评论界面语言，默认 en
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time

OUT_DIR = "out"
WORK_DIR = os.path.join(OUT_DIR, "_work")

QUERIES = [q.strip() for q in os.environ.get("QUERIES", "").split("|") if q.strip()]
VIDEO_IDS = [v.strip() for v in os.environ.get("VIDEO_IDS", "").split(",") if v.strip()]
CHANNELS = [c.strip() for c in os.environ.get("CHANNELS", "").split("|") if c.strip()]
MAX_COMMENTS = int(os.environ.get("MAX_COMMENTS", "0") or 0)
MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS", "0") or 0)
SORT = os.environ.get("SORT", "top") or "top"
LANG = os.environ.get("LANG_UI", "en") or "en"

DEFAULT_QUERIES = [
    "中餐厅 非洲创业季",
    "中餐厅 摩洛哥 丹吉尔",
    "中餐厅 第九季",
    "Chinese Restaurant variety show Morocco",
    "中餐厅 外国人反应",
    "Chinese Restaurant show foreigners reaction",
]


def run(args: list[str], timeout: int, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["yt-dlp"] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, check=check)


def cookie_args() -> list[str]:
    """可选：从 YT_COOKIES 环境变量加载 cookies。

    Secrets 里存 cookies.txt 的全文或 base64 均可。
    当 runner IP 被 YouTube 判定为机器人时，这是唯一有效的解法。
    """
    raw = (os.environ.get("YT_COOKIES") or "").strip()
    if not raw:
        return []
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "cookies.txt")
    if "\t" not in raw:  # 认为是 base64
        try:
            import base64
            raw = base64.b64decode(raw).decode("utf-8", "replace")
        except Exception:
            pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"[cookies] 已加载 {len(raw)} 字节")
    return ["--cookies", path]


def base_args() -> list[str]:
    args = ["--no-warnings", "--no-playlist",
            "--socket-timeout", os.environ.get("SOCKET_TIMEOUT", "30"),
            "--retries", os.environ.get("RETRIES", "3"),
            "--no-check-certificates"]
    proxy = (os.environ.get("YT_PROXY") or "").strip()
    if proxy:
        args += ["--proxy", proxy]
    return args + cookie_args()


def search(query: str, n: int = 15) -> list[dict]:
    try:
        p = run(base_args() + ["--flat-playlist", "--skip-download",
                               "--print", "%(id)s\t%(title)s",
                               f"ytsearch{n}:{query}"], 300)
    except Exception as e:
        print(f"  search failed: {query} -> {str(e)[:100]}")
        return []
    out = []
    for line in p.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and len(parts[0].strip()) == 11:
            out.append({"id": parts[0].strip(), "title": parts[1].strip(), "from": query})
    return out


def list_channel(url: str, limit: int = 80) -> list[dict]:
    try:
        p = run(base_args() + ["--flat-playlist", "--skip-download",
                               "--playlist-end", str(limit),
                               "--print", "%(id)s\t%(title)s", url], 600)
    except Exception as e:
        print(f"  channel failed: {url} -> {str(e)[:100]}")
        return []
    out = []
    for line in p.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and len(parts[0].strip()) == 11:
            out.append({"id": parts[0].strip(), "title": parts[1].strip(), "from": url})
    return out


def _fetch_once(video_id: str, client: str = "") -> tuple[list[dict], str]:
    os.makedirs(WORK_DIR, exist_ok=True)
    mc = f"{MAX_COMMENTS or 'all'},all,all,all"
    ea = f"youtube:comment_sort={SORT};max_comments={mc};lang={LANG}"
    if client:
        ea += f";player_client={client}"
    args = base_args() + [
        "--skip-download", "--write-comments", "--write-info-json",
        "--no-write-subs", "--no-write-auto-subs", "--no-write-thumbnail",
        "--sleep-requests", "2",
        "--extractor-args", ea,
        "-o", os.path.join(WORK_DIR, "%(id)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        run(args, 3600)
    except subprocess.TimeoutExpired:
        return [], "TIMEOUT"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or "")
        if "not a bot" in err or "Sign in to confirm" in err:
            return [], "BOT_CHECK"
        tail = err.strip().splitlines()[-2:]
        return [], (" | ".join(tail))[:200]

    info_path = os.path.join(WORK_DIR, f"{video_id}.info.json")
    if not os.path.exists(info_path):
        return [], "NO_INFO_JSON"
    with open(info_path, encoding="utf-8") as f:
        info = json.load(f)
    title = info.get("title") or ""
    rows = []
    for c in info.get("comments") or []:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        ts = c.get("timestamp")
        pt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts)) if ts else (c.get("_time_text") or "")
        rows.append({
            "platform": "YouTube",
            "platform_region": "海外",
            "video_id": video_id,
            "video_title": title,
            "cid": str(c.get("id") or ""),
            "publish_time": pt,
            "user_name": c.get("author") or "",
            "user_region": "",
            "text": text,
            "like": int(c.get("like_count") or 0),
            "reply_count": int(c.get("reply_count") or 0),
            "parent_cid": str(c.get("parent") or "root"),
            "raw": {"author_id": c.get("author_id", ""),
                    "is_uploader": c.get("author_is_uploader", False),
                    "time_text": c.get("_time_text", "")},
        })
    return rows, title


def fetch(video_id: str) -> tuple[list[dict], str]:
    """带降级的抓取：默认客户端 → web_safari → tv。机器人校验时不空转重试。"""
    rows, info = _fetch_once(video_id)
    if rows or info not in ("BOT_CHECK", "NO_INFO_JSON"):
        return rows, info
    for client in ("web_safari", "tv"):
        print(f"    降级 client={client} 重试…")
        rows, info = _fetch_once(video_id, client)
        if rows:
            return rows, info
        if info == "BOT_CHECK":
            break
    return [], info


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=" * 60)
    print(f"max_comments={MAX_COMMENTS} max_videos={MAX_VIDEOS} sort={SORT}")

    # 1) 视频清单
    if VIDEO_IDS:
        videos = [{"id": v, "title": "", "from": "manual"} for v in VIDEO_IDS]
        print(f"使用手工指定视频 {len(videos)} 条")
    else:
        found: dict[str, dict] = {}
        for q in (QUERIES or DEFAULT_QUERIES):
            vs = search(q)
            print(f"[search] {q} -> {len(vs)}")
            for v in vs:
                found.setdefault(v["id"], v)
            time.sleep(1)
        for ch in CHANNELS:
            vs = list_channel(ch)
            print(f"[channel] {ch} -> {len(vs)}")
            for v in vs:
                found.setdefault(v["id"], v)
        videos = list(found.values())

    with open(os.path.join(OUT_DIR, "yt_videos.json"), "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f"共 {len(videos)} 条候选视频")

    if MAX_VIDEOS:
        videos = videos[:MAX_VIDEOS]

    # 2) 抓评论
    all_rows, failed = [], []
    for i, v in enumerate(videos, 1):
        vid = v["id"]
        rows, title = fetch(vid)
        if not rows:
            print(f"[{i}/{len(videos)}] {vid} 无评论/失败: {title}")
            failed.append(f"{vid}\t{title}")
            continue
        all_rows += rows
        print(f"[{i}/{len(videos)}] {vid} {len(rows):>6} 条 | {(title or v.get('title',''))[:55]}")
        # 落盘，避免中途失败全丢
        with open(os.path.join(OUT_DIR, "raw_youtube.jsonl"), "w", encoding="utf-8") as f:
            for r in all_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        time.sleep(2)

    # 3) 输出
    jl = os.path.join(OUT_DIR, "raw_youtube.jsonl")
    with open(jl, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cols = ["platform", "platform_region", "video_id", "video_title", "cid",
            "publish_time", "user_name", "user_region", "text", "like",
            "reply_count", "parent_cid"]
    with open(os.path.join(OUT_DIR, "raw_youtube.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    with open(os.path.join(OUT_DIR, "failed.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(failed))

    bot = sum(1 for x in failed if "BOT_CHECK" in x)
    status = {
        "videos": len(videos),
        "comments": len(all_rows),
        "failed": len(failed),
        "bot_check": bot,
        "cookies_loaded": bool((os.environ.get("YT_COOKIES") or "").strip()),
    }
    with open(os.path.join(OUT_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"完成：{len(all_rows)} 条评论，{len(videos)} 条视频，失败 {len(failed)} 条")
    if bot:
        print(f"\n[!] {bot} 条视频被 YouTube 判定为机器人（BOT_CHECK）。")
        print("    说明本次 runner 出口 IP 信誉被标记。三条出路：")
        print("    1) 重跑一次（runner IP 每次不同，可能抽到干净的）")
        print("    2) 加 YT_COOKIES secret（找能上 YouTube 的人导出 cookies.txt）")
        print("    3) 改用国内可买的海外代理，3 元/GB，见 remote/README_出口方案.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
