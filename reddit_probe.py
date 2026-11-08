import json, requests
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"}
tests = [
    ("old.reddit",   "https://old.reddit.com/search.json", {"q": "Chinese Restaurant S9", "limit": 5}),
    ("api.reddit",   "https://api.reddit.com/search.json", {"q": "Chinese Restaurant S9", "limit": 5}),
    ("www.reddit",   "https://www.reddit.com/search.json", {"q": "Chinese Restaurant S9", "limit": 5}),
    ("arctic-posts", "https://arctic-shift.photon-reddit.com/api/posts/search",
     {"query": "Chinese Restaurant", "subreddit": "cdrama", "size": 5}),
    ("arctic-comm",  "https://arctic-shift.photon-reddit.com/api/comments/search",
     {"query": "Chinese Restaurant S9", "size": 5}),
    ("hn-algolia",   "https://hn.algolia.com/api/v1/search", {"query": "chinese restaurant", "hitsPerPage": 5}),
]
for name, url, params in tests:
    try:
        r = requests.get(url, params=params, headers=H, timeout=25)
        body = r.text[:200].replace("\n", " ")
        print(f"[{name}] {r.status_code} len={len(r.text)}")
        print("   ", body)
        if r.status_code == 200:
            try:
                d = r.json()
                if isinstance(d, dict):
                    if "data" in d and "children" in d["data"]:
                        print("    children:", len(d["data"]["children"]))
                        for ch in d["data"]["children"][:3]:
                            print("      -", ch["data"].get("title", "")[:70])
                    elif "hits" in d:
                        print("    hits:", len(d["hits"]))
                    elif "data" in d and isinstance(d["data"], list):
                        print("    data rows:", len(d["data"]))
                        for x in d["data"][:3]:
                            print("      -", str(x)[:120])
            except Exception as e:
                print("    json err", e)
    except Exception as e:
        print(f"[{name}] ERR {str(e)[:100]}")
