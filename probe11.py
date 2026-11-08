import json, requests, urllib.parse
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 Chrome/122.0"})
Q = urllib.parse.quote("中餐厅")
targets = [
    ("old_reddit", f"https://old.reddit.com/r/CDrama/search?q={Q}&restrict_sr=on"),
    ("facebook", "https://www.facebook.com/MangoTV"),
    ("threads", f"https://www.threads.net/search?q={Q}"),
    ("ig_post", "https://www.instagram.com/explore/tags/chineserestaurant/"),
]
out = {}
for name, url in targets:
    try:
        r = S.get("https://r.jina.ai/" + url, timeout=90, headers={"X-Return-Format": "text"})
        print(f"[{name}] {r.status_code} len={len(r.text)}")
        print("   ", r.text[:260].replace("\n", " "))
        out[name] = {"code": r.status_code, "len": len(r.text), "head": r.text[:1200]}
    except Exception as e:
        print(f"[{name}] ERR {str(e)[:80]}")
json.dump(out, open("out/probe11.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
