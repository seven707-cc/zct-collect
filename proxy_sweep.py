#!/usr/bin/env python3
"""在 runner 上扫描免费代理池，找出能访问 YouTube 的出口。

思路：runner 本身能访问 YouTube 的普通页面，但评论接口被判定为机器人。
若找到可用的 HTTP 代理，用 yt-dlp --proxy 走它抓评论即可。
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time

import requests

VIDEO = os.environ.get("PROBE_VIDEO", "oRhkf2hNcdQ")
MAXC = os.environ.get("PROBE_MAX", "10")
TEST_URL = f"https://www.youtube.com/watch?v={VIDEO}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"}

SOURCES = [
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt",
]


def collect() -> list[str]:
    out: list[str] = []
    for u in SOURCES:
        try:
            r = requests.get(u, timeout=25, headers=UA)
            if r.status_code != 200:
                print(f"[src] {u.split('/')[-3]} -> {r.status_code}")
                continue
            found = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b", r.text)
            out += [f"{ip}:{p}" for ip, p in found]
            print(f"[src] {u.split('/')[-3]} -> {len(found)}")
        except Exception as e:
            print(f"[src] {u.split('/')[-3]} err {str(e)[:60]}")
    seen, uniq = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    print(f"[src] 去重后 {len(uniq)} 个代理")
    return uniq


def test(addr: str) -> dict | None:
    px = {"http": f"http://{addr}", "https": f"http://{addr}"}
    try:
        r = requests.get(TEST_URL, proxies=px, headers=UA, timeout=9, stream=True)
        if r.status_code != 200:
            return None
        body = r.raw.read(200000, decode_content=True).decode("utf-8", "replace")
        if "ytInitialData" not in body:
            return None
        return {"addr": addr, "len": len(body)}
    except Exception:
        return None


def try_comments(addr: str) -> dict:
    tmp = f"/tmp/c_{addr.replace(':','_')}"
    os.makedirs(tmp, exist_ok=True)
    args = ["yt-dlp", "--no-warnings", "--skip-download", "--write-comments",
            "--write-info-json", "--no-write-subs", "--no-write-auto-subs",
            "--no-write-thumbnail", "--no-playlist", "--socket-timeout", "20",
            "--retries", "1", "--proxy", f"http://{addr}",
            "--extractor-args", f"youtube:max_comments={MAXC},all,all,all",
            "-o", os.path.join(tmp, "%(id)s"), TEST_URL]
    t0 = time.time()
    try:
        subprocess.run(args, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return {"addr": addr, "comments": 0, "err": "TIMEOUT"}
    ip = os.path.join(tmp, f"{VIDEO}.info.json")
    n = 0
    if os.path.exists(ip):
        try:
            n = len(json.load(open(ip, encoding="utf-8")).get("comments") or [])
        except Exception:
            pass
    return {"addr": addr, "comments": n, "sec": round(time.time() - t0, 1)}


def main() -> None:
    addrs = collect()
    if not addrs:
        print("没有取到代理列表")
        return
    ok = []
    with cf.ThreadPoolExecutor(max_workers=120) as ex:
        for r in ex.map(test, addrs[:1500]):
            if r:
                ok.append(r["addr"])
                print(f"[可用] {r['addr']}  (ytInitialData OK)")
    print(f"\n可打开 YouTube 页面的代理：{len(ok)} 个")

    good = []
    for a in ok[:40]:
        res = try_comments(a)
        print(f"[评论测试] {a:<22} n={res['comments']}")
        if res["comments"] > 0:
            good.append(res)
            print(f"  *** {a} 成功抓到 {res['comments']} 条 ***")
            break
    json.dump({"proxies": ok, "working": good}, open("proxy_result.json", "w"), ensure_ascii=False, indent=2)
    print("结果已写 proxy_result.json")


if __name__ == "__main__":
    main()
