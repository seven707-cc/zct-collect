import json, requests
H = {"User-Agent": "academic-research/0.1"}
base = "https://arctic-shift.photon-reddit.com/api"
tests = [
    ("posts q",  f"{base}/posts/search",    {"q": "Chinese Restaurant", "limit": 5, "sort": "desc"}),
    ("posts cd", f"{base}/posts/search",    {"q": "Chinese Restaurant", "subreddit": "cdrama", "limit": 5}),
    ("comm  q",  f"{base}/comments/search", {"q": "Chinese Restaurant", "limit": 5}),
    ("comm cd",  f"{base}/comments/search", {"q": "Chinese Restaurant", "subreddit": "cdrama", "limit": 5}),
]
for name, url, params in tests:
    try:
        r = requests.get(url, params=params, headers=H, timeout=30)
        print(f"[{name}] {r.status_code} len={len(r.text)}")
        if r.status_code == 200:
            d = r.json()
            rows = d.get("data") or []
            print("   rows:", len(rows))
            for x in rows[:3]:
                print("    -", x.get("subreddit"), "|", (x.get("title") or x.get("body") or "")[:80], "| score", x.get("score"))
        else:
            print("   ", r.text[:150])
    except Exception as e:
        print(f"[{name}] ERR {str(e)[:100]}")
