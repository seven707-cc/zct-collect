import json, re, requests
S = requests.Session(); S.headers.update({"User-Agent": "Mozilla/5.0 Chrome/122.0"})

def jina(url, fmt="markdown"):
    try:
        r = S.get("https://r.jina.ai/" + url, timeout=90, headers={"X-Return-Format": fmt})
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)[:150]

out = {}
handles = ["mangotv.official", "mangotv", "mgtv", "mangotv_official", "official.mangotv"]
for h in handles:
    c, t = jina(f"https://www.instagram.com/{h}/")
    posts = list(dict.fromkeys(re.findall(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]{8,15})", t)))
    login = "Log into Instagram" in t
    print(f"[ig] @{h}: {c} len={len(t)} login={login} posts={len(posts)}")
    out[h] = {"code": c, "len": len(t), "login": login, "posts": posts[:24], "head": t[:600]}
    if posts:
        c2, t2 = jina(f"https://www.instagram.com/p/{posts[0]}/")
        out[f"post::{posts[0]}"] = {"code": c2, "len": len(t2), "text": t2[:2000]}
        print("   sample post:", t2[:300].replace("\n", " | "))
json.dump(out, open("out/probe14.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
