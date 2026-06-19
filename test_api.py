import asyncio
import httpx
import re
import json

data = json.load(open("data/stores.json"))
store = list(data["stores"].values())[0]
cookie = store["cookie"]
url = store["url"]
print(f"Store: {store['name']}")
print(f"URL: {url}")


async def test():
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        cookies={"_website_session_7": cookie},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        r = await client.get(
            "https://www.enjoei.com.br/api/session/csrf_meta.json?version=v1"
        )
        print(f"\nCSRF status: {r.status_code}")
        print(f"CSRF response: {r.text[:200]}")

        r = await client.get(url)
        print(f"\nStore page status: {r.status_code}")
        print(f"Store page length: {len(r.text)} chars")

        ids = set()
        for m in re.findall(r'/p/[^"\s]*?-(\d{5,})', r.text):
            ids.add(m)
        for m in re.findall(r'product_id["\s:=]+(\d{5,})', r.text, re.IGNORECASE):
            ids.add(m)
        for m in re.findall(r'"id"\s*:\s*(\d{5,})', r.text):
            ids.add(m)
        print(f"\nProduct IDs found: {len(ids)}")
        print(f"IDs: {list(ids)[:10]}")

        with open("debug_page.html", "w") as f:
            f.write(r.text)
        print("\nFull HTML saved to debug_page.html")


asyncio.run(test())
