#!/usr/bin/env python3
"""第四轮：台港平台（PTT / Dcard / LIHKG）+ Instagram 标签接口。"""
from __future__ import annotations

import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}


def show(tag, r, extra=""):
    print(f"[{tag}] {r.status_code} len={len(r.content)} {extra}")
    print("   ", r.text[:180].replace("\n", " "))


def ptt():
    for board in ["CN_Entertain", "TW_Entertain", "CN_Ent"]:
        try:
            r = S.get(f"https://www.ptt.cc/bbs/{board}/search", params={"q": "中餐廳"}, timeout=25)
            titles = re.findall(r'<div class="title">\s*<a href="([^"]+)">([^<]+)</a>', r.text)
            print(f"[ptt/{board}] {r.status_code} hits={len(titles)}")
            for h, t in titles[:8]:
                print("   -", t.strip()[:70])
            RES[f"ptt/{board}"] = {"status": r.status_code, "hits": len(titles),
                                   "items": [{"url": h, "title": t.strip()} for h, t in titles[:30]]}
        except Exception as e:
            print(f"[ptt/{board}] ERR {str(e)[:70]}")
            RES[f"ptt/{board}"] = {"err": str(e)[:100]}


def dcard():
    for q in ["中餐廳", "中餐厅"]:
        try:
            r = S.get("https://www.dcard.tw/service/api/v2/search/posts",
                      params={"query": q, "limit": 30}, timeout=25,
                      headers={"Referer": "https://www.dcard.tw/"})
            n = len(r.json()) if r.status_code == 200 else 0
            print(f"[dcard] {q} {r.status_code} n={n}")
            if n:
                for p in r.json()[:5]:
                    print("   -", p.get("title", "")[:60], "|", p.get("commentCount"))
            RES[f"dcard::{q}"] = {"status": r.status_code, "n": n}
        except Exception as e:
            print(f"[dcard] {q} ERR {str(e)[:70]}")
            RES[f"dcard::{q}"] = {"err": str(e)[:100]}


def lihkg():
    for q in ["中餐廳", "中餐厅"]:
        try:
            r = S.get("https://lihkg.com/api_v2/thread/search",
                      params={"q": q, "page": 1, "count": 30}, timeout=25,
                      headers={"Referer": "https://lihkg.com/", "X-Requested-With": "XMLHttpRequest"})
            ok = r.status_code == 200
            data = r.json() if ok else {}
            items = (data.get("response") or {}).get("items") or []
            print(f"[lihkg] {q} {r.status_code} n={len(items)}")
            for it in items[:5]:
                print("   -", str(it.get("title"))[:60], "|", it.get("no_of_reply"))
            RES[f"lihkg::{q}"] = {"status": r.status_code, "n": len(items)}
        except Exception as e:
            print(f"[lihkg] {q} ERR {str(e)[:70]}")
            RES[f"lihkg::{q}"] = {"err": str(e)[:100]}


def instagram():
    IG = {"x-ig-app-id": "936619743392459", "User-Agent": UA, "Referer": "https://www.instagram.com/"}
    for tag in ["中餐厅", "chineserestaurant"]:
        try:
            r = S.get("https://www.instagram.com/api/v1/tags/web_info/",
                      params={"tag_name": tag}, headers=IG, timeout=25)
            d = r.json() if r.status_code == 200 else {}
            media = ((d.get("data") or {}).get("recent") or {}).get("sections") or []
            n = sum(len(s.get("layout_content", {}).get("medias", [])) for s in media)
            print(f"[ig] #{tag} {r.status_code} medias={n}")
            RES[f"ig::{tag}"] = {"status": r.status_code, "medias": n}
        except Exception as e:
            print(f"[ig] #{tag} ERR {str(e)[:70]}")
            RES[f"ig::{tag}"] = {"err": str(e)[:100]}


def tiktok():
    """不带签名的公开接口，看错误类型"""
    for url, params in [
        ("https://www.tiktok.com/api/search/general/full", {"keyword": "中餐厅9", "count": 10}),
        ("https://www.tiktok.com/api/comment/list/", {"aweme_id": "7530000000000000000", "count": 20}),
    ]:
        try:
            r = S.get(url, params=params, timeout=25,
                      headers={"Referer": "https://www.tiktok.com/"})
            print(f"[tt] {url.split('/api')[-1]} {r.status_code} {r.text[:160]}")
            RES[f"tt::{url.split('/api')[-1]}"] = {"status": r.status_code, "head": r.text[:200]}
        except Exception as e:
            print(f"[tt] ERR {str(e)[:70]}")


def main():
    ptt()
    dcard()
    lihkg()
    instagram()
    tiktok()
    with open("out/probe4.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
