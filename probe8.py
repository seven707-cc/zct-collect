#!/usr/bin/env python3
"""第八轮：绕开 TikTok 签名墙——先用搜索引擎找视频 URL，再看页面内嵌 JSON 是否有评论。"""
from __future__ import annotations

import json
import re
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}


def ddg(q: str) -> list[str]:
    urls = []
    for host in ["https://html.duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"]:
        try:
            r = S.post(host, data={"q": q}, timeout=25)
            print(f"[ddg] {host} {r.status_code} len={len(r.content)}")
            found = re.findall(r"(https?://(?:www\.)?tiktok\.com/@[\w.\-]+/video/\d+)", r.text)
            found += re.findall(r"uddg=([^\"&]+)", r.text)
            for f in found:
                f = urllib.parse.unquote(f)
                if "tiktok.com" in f:
                    urls.append(f)
            if urls:
                break
        except Exception as e:
            print(f"[ddg] {host} ERR {str(e)[:60]}")
    return list(dict.fromkeys(urls))


def bing(q: str) -> list[str]:
    try:
        r = S.get("https://www.bing.com/search", params={"q": q, "count": 30}, timeout=25)
        print(f"[bing] {r.status_code} len={len(r.content)}")
        found = re.findall(r"(https?://(?:www\.)?tiktok\.com/@[\w.\-]+/video/\d+)", r.text)
        return list(dict.fromkeys(found))
    except Exception as e:
        print(f"[bing] ERR {str(e)[:60]}")
        return []


def check_page(url: str) -> dict:
    try:
        r = S.get(url, timeout=30, headers={"Accept-Language": "en-US,en;q=0.9"})
        t = r.text
        has_sigi = "__UNIVERSAL_DATA_FOR_REHYDRATION__" in t or "SIGI_STATE" in t
        n_comment = len(re.findall(r'"commentList"', t))
        cids = re.findall(r'"cid":"(\d{15,25})"', t)[:5]
        print(f"[tt] {url[-40:]} {r.status_code} len={len(t)} sigi={has_sigi} "
              f"commentList={n_comment} cids={len(cids)}")
        return {"status": r.status_code, "len": len(t), "sigi": has_sigi,
                "commentList": n_comment, "cids": cids,
                "head": re.sub(r"\s+", " ", t[:200])}
    except Exception as e:
        print(f"[tt] ERR {str(e)[:60]}")
        return {"err": str(e)[:100]}


def main():
    queries = [
        "site:tiktok.com 中餐厅9",
        "site:tiktok.com chinese restaurant 9 mangotv",
        "site:tiktok.com 丁禹兮 中餐厅",
        "site:tiktok.com ding yuxi chinese restaurant",
    ]
    all_urls: list[str] = []
    for q in queries:
        u = ddg(q) or bing(q)
        print(f"[q] {q} -> {len(u)} urls")
        all_urls += u
    all_urls = list(dict.fromkeys(all_urls))
    print("合计 tiktok url", len(all_urls))
    for u in all_urls[:5]:
        print("  ", u)
    RES["urls"] = all_urls[:50]
    RES["pages"] = [check_page(u) for u in all_urls[:3]]

    with open("out/probe8.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
