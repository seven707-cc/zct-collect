import json, re, requests, urllib.parse
S = requests.Session(); S.headers.update({"User-Agent": "Mozilla/5.0 Chrome/122.0"})

def jina(url, fmt="text"):
    try:
        r = S.get("https://r.jina.ai/" + url, timeout=90, headers={"X-Return-Format": fmt})
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)[:150]

out = {}
# 1) IG 标签页，抓帖子短链
for tag in ["%E4%B8%AD%E9%A4%90%E5%8E%85", "chineserestaurant9"]:
    code, txt = jina(f"https://www.instagram.com/explore/tags/{tag}/", "markdown")
    posts = list(dict.fromkeys(re.findall(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]{8,15})", txt)))
    print(f"[ig-tag] {tag} {code} len={len(txt)} posts={len(posts)}")
    out[f"tag::{tag}"] = {"code": code, "len": len(txt), "posts": posts[:20],
                          "head": txt[:800]}
    if posts:
        c2, t2 = jina(f"https://www.instagram.com/p/{posts[0]}/")
        print(f"[ig-post] {posts[0]} {c2} len={len(t2)}")
        out[f"post::{posts[0]}"] = {"code": c2, "len": len(t2), "text": t2[:2500]}

# 2) Dailymotion 视频页
c3, t3 = jina("https://www.dailymotion.com/video/x8nnzxc")
print(f"[dm] {c3} len={len(t3)}")
out["dm"] = {"code": c3, "len": len(t3), "text": t3[:1500]}

json.dump(out, open("out/probe12.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
