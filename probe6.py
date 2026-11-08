#!/usr/bin/env python3
"""第六轮：ProxiTok（TikTok 镜像）+ 港/海外华人论坛。"""
from __future__ import annotations

import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
RES: dict = {}

PROXITOK = [
    "https://proxitok.pabloferreiro.es",
    "https://proxitok.privacydev.net",
    "https://proxitok.pussthecat.org",
    "https://tok.artemislena.eu",
    "https://tok.hostux.net",
    "https://proxitok.esmailelbob.xyz",
    "https://tt.vern.cc",
    "https://proxitok.lunar.icu",
]


def proxitok():
    out = {}
    for base in PROXITOK:
        try:
            r = S.get(base + "/", timeout=15)
            print(f"[proxitok] {base} -> {r.status_code} len={len(r.content)}")
            if r.status_code != 200:
                out[base] = {"status": r.status_code}
                continue
            # 搜索页
            for q in ["中餐厅", "chinese restaurant 9"]:
                import urllib.parse
                u = f"{base}/search?q={urllib.parse.quote(q)}"
                rr = S.get(u, timeout=25)
                vids = set(re.findall(r"/@([\w.\-]+)/video/(\d+)", rr.text))
                print(f"   search {q}: {rr.status_code} videos={len(vids)}")
                if vids:
                    print("     sample:", list(vids)[:3])
                out.setdefault(base, {})[f"search::{q}"] = {
                    "status": rr.status_code, "videos": [f"{a}/{v}" for a, v in list(vids)[:50]]}
        except Exception as e:
            print(f"[proxitok] {base} ERR {str(e)[:60]}")
            out[base] = {"err": str(e)[:100]}
    RES["proxitok"] = out


def forums():
    out = {}
    targets = [
        ("discuss_hk", "https://www.discuss.com.hk/search.php?srchtxt=%A4%A4%C0%5D%C4U"),
        ("uwants", "https://www.uwants.com/search.php?srchtxt=%A4%A4%C0%5D%C4U"),
        ("6park", "https://www.6park.com/enter4/"),
        ("wenxuecity", "https://bbs.wenxuecity.com/"),
        ("cari", "https://www.cari.com.my/forum.php?mod=forumdisplay&fid=9"),
        ("hk01", "https://www.hk01.com/搜尋?q=中餐廳"),
    ]
    for name, url in targets:
        try:
            r = S.get(url, timeout=20)
            print(f"[{name}] {r.status_code} len={len(r.content)}")
            out[name] = {"status": r.status_code, "len": len(r.content),
                         "head": re.sub(r"<[^>]+>", " ", r.text)[:150]}
        except Exception as e:
            print(f"[{name}] ERR {str(e)[:60]}")
            out[name] = {"err": str(e)[:100]}
    RES["forums"] = out


def main():
    proxitok()
    forums()
    with open("out/probe6.json", "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
