import json, re, requests, urllib.parse
S = requests.Session(); S.headers.update({"User-Agent": "Mozilla/5.0 Chrome/122.0"})

def jina(url, fmt="markdown"):
    try:
        r = S.get("https://r.jina.ai/" + url, timeout=90, headers={"X-Return-Format": fmt})
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)[:150]

tags = ["中餐厅9", "中餐厅非洲创业季", "丁禹兮", "dingyuxi", "姜妍", "chineserestaurantseason9"]
out = {}
allposts = []
for t in tags:
    q = urllib.parse.quote(t)
    code, txt = jina(f"https://www.instagram.com/explore/tags/{q}/")
    gated = "Log into Instagram" in txt or "/accounts/login/" in txt
    posts = list(dict.fromkeys(re.findall(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]{8,15})", txt)))
    print(f"[tag] {t}: {code} len={len(txt)} gated={gated} posts={len(posts)}")
    out[t] = {"code": code, "len": len(txt), "gated": gated, "posts": posts[:30],
              "head": txt[:500]}
    allposts += posts
allposts = list(dict.fromkeys(allposts))
print("total posts", len(allposts))
out["_all"] = allposts[:60]
# 看一个帖子页的完整结构（找评论格式）
if allposts:
    c, t = jina(f"https://www.instagram.com/p/{allposts[0]}/")
    print(f"[post] {allposts[0]} {c} len={len(t)}")
    out["_sample_post"] = t[:3000]
    print(t[:1200].replace("\n", " | "))
json.dump(out, open("out/probe13.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
