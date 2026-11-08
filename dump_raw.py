import json, yt_instances as yi
yi.VIDEO_ID = "MU0qexL9obc"
ok = yi.probe_all(yi.discover())
good = sorted(ok, key=lambda x: -x["n"])[:2]
for g in good:
    r = yi.S.get(f"{g['base']}/api/v1/comments/MU0qexL9obc", timeout=25)
    if r.status_code == 200:
        d = r.json()
        print("BASE", g["base"])
        for c in (d.get("comments") or [])[:2]:
            print(json.dumps(c, ensure_ascii=False)[:900])
        print("KEYS", list((d.get("comments") or [{}])[0].keys()))
        break
