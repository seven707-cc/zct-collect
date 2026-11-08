#!/usr/bin/env python3
"""通过 Invidious / Piped 公共实例抓 YouTube 评论。

原理：这些站点是 YouTube 的第三方镜像前端，评论由它们的服务器代为请求，
不存在「Sign in to confirm you're not a bot」问题，直接返回 JSON。

环境变量：
    MODE        probe（只测哪些实例可用） / collect（正式采集）
    VIDEO_ID    单个视频，或
    VIDEO_IDS   多个视频，逗号分隔
    MAX_COMMENTS 每条视频最多多少条，0=不限
    OUT_DIR     输出目录，默认 out
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
OUT_DIR = os.environ.get("OUT_DIR", "out")
MODE = os.environ.get("MODE", "probe")
MAX_COMMENTS = int(os.environ.get("MAX_COMMENTS", "0") or 0)
VIDEO_ID = os.environ.get("VIDEO_ID", "oRhkf2hNcdQ")
VIDEO_IDS = [v.strip() for v in os.environ.get("VIDEO_IDS", "").split(",") if v.strip()]

S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept": "application/json"})

INVIDIOUS_STATIC = [
    "https://inv.nadeko.net", "https://invidious.nerdvpn.de", "https://yewtu.be",
    "https://invidious.f5.si", "https://iv.melmac.space", "https://invidious.jing.rocks",
    "https://invidious.privacyredirect.com", "https://invidious.einfachzocken.eu",
    "https://inv.tux.pizza", "https://invidious.lunivers.trade", "https://inv.zzls.xyz",
    "https://invidious.private.coffee", "https://vid.puffyan.us", "https://inv.riverside.rocks",
    "https://invidious.dhusch.de", "https://invidious.nikkosphere.com", "https://yt.artemislena.eu",
    "https://invidious.perennialte.ch", "https://iv.datura.network", "https://invidious.materialio.us",
]

PIPED_STATIC = [
    "https://pipedapi.kavin.rocks", "https://pipedapi.adminforge.de",
    "https://api.piped.private.coffee", "https://pipedapi.reallyaweso.me",
    "https://pipedapi.drgns.space", "https://pipedapi.darkness.services",
    "https://pipedapi.ducks.party", "https://piped-api.lunar.icu",
    "https://pipedapi.orangenet.cc", "https://pipedapi.leptons.xyz",
]


def discover() -> list[tuple[str, str]]:
    """返回 [(kind, base_url)]，kind = invidious / piped"""
    out: list[tuple[str, str]] = []
    try:
        r = S.get("https://api.invidious.io/instances.json?sort_by=health", timeout=25)
        if r.status_code == 200:
            for name, info in r.json():
                if info.get("type") != "https" or info.get("api") is False:
                    continue
                uri = info.get("uri") or f"https://{name}"
                out.append(("invidious", uri.rstrip("/")))
            print(f"[discover] invidious 目录 {len(out)} 个")
    except Exception as e:
        print(f"[discover] invidious 目录失败 {str(e)[:80]}")

    try:
        r = S.get("https://piped-instances.kavin.rocks/", timeout=25)
        if r.status_code == 200:
            n0 = len(out)
            for it in r.json():
                api = (it.get("api_url") or "").rstrip("/")
                if api:
                    out.append(("piped", api))
            print(f"[discover] piped 目录 {len(out) - n0} 个")
    except Exception as e:
        print(f"[discover] piped 目录失败 {str(e)[:80]}")

    for u in INVIDIOUS_STATIC:
        out.append(("invidious", u))
    for u in PIPED_STATIC:
        out.append(("piped", u))

    seen, uniq = set(), []
    for k, u in out:
        if u not in seen:
            seen.add(u)
            uniq.append((k, u))
    return uniq


def probe_one(item: tuple[str, str]) -> dict | None:
    kind, base = item
    t0 = time.time()
    try:
        if kind == "invidious":
            url = f"{base}/api/v1/comments/{VIDEO_ID}"
            r = S.get(url, timeout=12)
            if r.status_code != 200:
                return None
            d = r.json()
            cs = d.get("comments") or []
        else:
            url = f"{base}/comments/{VIDEO_ID}"
            r = S.get(url, timeout=12)
            if r.status_code != 200:
                return None
            d = r.json()
            cs = d.get("comments") or []
        if not cs:
            return None
        return {"kind": kind, "base": base, "n": len(cs),
                "sec": round(time.time() - t0, 1),
                "total": d.get("commentCount") or 0,
                "sample": (cs[0].get("content") or cs[0].get("commentText") or "")[:60]}
    except Exception:
        return None


def probe_all(items: list[tuple[str, str]]) -> list[dict]:
    ok = []
    with cf.ThreadPoolExecutor(max_workers=30) as ex:
        for r in ex.map(probe_one, items):
            if r:
                ok.append(r)
                print(f"[可用] {r['kind']:<9} {r['base']:<42} {r['n']} 条  总{r['total']}  {r['sec']}s")
    return ok


def norm_invidious(c: dict, vid: str, title: str) -> dict:
    pub = c.get("published")
    pt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(pub)) if pub else (c.get("publishedText") or "")
    return {
        "platform": "YouTube", "platform_region": "海外",
        "video_id": vid, "video_title": title,
        "cid": c.get("commentId") or "",
        "publish_time": pt,
        "user_name": c.get("author") or "",
        "user_region": "",
        "text": (c.get("content") or "").strip(),
        "like": int(c.get("likeCount") or 0),
        "reply_count": int((c.get("replies") or {}).get("replyCount") or 0),
        "parent_cid": "root",
        "raw": {"author_id": c.get("authorId", ""),
                "is_uploader": c.get("authorIsChannelOwner", False),
                "source": "invidious"},
    }


def norm_piped(c: dict, vid: str, title: str) -> dict:
    return {
        "platform": "YouTube", "platform_region": "海外",
        "video_id": vid, "video_title": title,
        "cid": c.get("commentId") or "",
        "publish_time": c.get("commentedTime") or "",
        "user_name": c.get("author") or "",
        "user_region": "",
        "text": (c.get("commentText") or "").strip(),
        "like": int(c.get("likeCount") or 0),
        "reply_count": int(c.get("replyCount") or 0),
        "parent_cid": "root",
        "raw": {"author_id": c.get("authorId", ""),
                "is_uploader": c.get("channelOwner", False),
                "source": "piped"},
    }


def get_title(kind: str, base: str, vid: str) -> str:
    try:
        url = (f"{base}/api/v1/videos/{vid}" if kind == "invidious"
               else f"{base}/streams/{vid}")
        r = S.get(url, timeout=15)
        if r.status_code == 200:
            return r.json().get("title") or ""
    except Exception:
        pass
    return ""


def collect(kind: str, base: str, vid: str, limit: int) -> list[dict]:
    title = get_title(kind, base, vid)
    rows: list[dict] = []
    cont = None
    page = 0
    while True:
        page += 1
        try:
            if kind == "invidious":
                url = f"{base}/api/v1/comments/{vid}"
                params = {"continuation": cont} if cont else {}
                r = S.get(url, params=params, timeout=20)
            else:
                if cont:
                    url = f"{base}/nextpage/comments/{vid}"
                    r = S.get(url, params={"nextpage": cont}, timeout=20)
                else:
                    r = S.get(f"{base}/comments/{vid}", timeout=20)
            if r.status_code != 200:
                print(f"    page{page} HTTP {r.status_code}")
                break
            d = r.json()
        except Exception as e:
            print(f"    page{page} err {str(e)[:70]}")
            break

        cs = d.get("comments") or []
        if not cs:
            break
        for c in cs:
            row = (norm_invidious(c, vid, title) if kind == "invidious"
                   else norm_piped(c, vid, title))
            if row["text"]:
                rows.append(row)
        print(f"    page{page}: +{len(cs)} 累计 {len(rows)}")
        if limit and len(rows) >= limit:
            break
        cont = d.get("continuation") if kind == "invidious" else d.get("nextpage")
        if not cont:
            break
        time.sleep(0.8)
        if page > 200:
            break
    return rows[:limit] if limit else rows


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    items = discover()
    print(f"[probe] 待测实例 {len(items)} 个")
    ok = probe_all(items)
    good = sorted(ok, key=lambda x: -x["n"])[:6]
    with open(os.path.join(OUT_DIR, "instances.json"), "w", encoding="utf-8") as f:
        json.dump({"tested": len(items), "working": ok}, f, ensure_ascii=False, indent=2)
    print(f"\n[probe] 可用实例 {len(ok)} 个")
    if not ok:
        print("没有可用实例")
        return 1
    if MODE == "probe":
        return 0

    vids = VIDEO_IDS or [VIDEO_ID]
    all_rows: list[dict] = []
    for i, vid in enumerate(vids, 1):
        print(f"\n[{i}/{len(vids)}] {vid}")
        rows: list[dict] = []
        for cand in good:
            rows = collect(cand["kind"], cand["base"], vid, MAX_COMMENTS)
            if rows:
                print(f"  用 {cand['base']} 拿到 {len(rows)} 条")
                break
            print(f"  {cand['base']} 失败，换下一个实例")
        all_rows += rows
        with open(os.path.join(OUT_DIR, "raw_youtube.jsonl"), "w", encoding="utf-8") as f:
            for r in all_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n合计 {len(all_rows)} 条评论，{len(vids)} 条视频")
    with open(os.path.join(OUT_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump({"videos": len(vids), "comments": len(all_rows),
                   "instances_ok": len(ok)}, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
