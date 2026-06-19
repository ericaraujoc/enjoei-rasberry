import asyncio
import httpx
import json

data = json.load(open("data/stores.json"))
store = list(data["stores"].values())[0]
cookie = store["cookie"]
url = store["url"]
handle = url.split("@")[-1].strip("/")
print(f"Store: {store['name']}")
print(f"URL: {url}")
print(f"Handle: {handle}")

BASE = "https://www.enjoei.com.br"
SEARCH = "https://enjusearch.enjoei.com.br/graphql"


async def test():
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        cookies={"_website_session_7": cookie},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        # 1. Try store API
        for path in [
            f"/api/stores/@{handle}",
            f"/api/users/@{handle}",
            f"/@{handle}.json",
            f"/api/store/{handle}",
        ]:
            r = await client.get(BASE + path)
            print(f"\n{path} -> {r.status_code}")
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application"):
                print(r.text[:500])

        # 2. Try minha-lojinha (my store page for logged in user)
        r = await client.get(BASE + "/perfil/minha-lojinha")
        print(f"\n/perfil/minha-lojinha -> {r.status_code}, {len(r.text)} chars")

        # 3. Try megaphone stats
        r = await client.get(BASE + "/api/megaphones/stats", params={"version": "v1"})
        print(f"\n/api/megaphones/stats -> {r.status_code}")
        if r.status_code == 200:
            print(r.text[:500])

        # 4. Try GraphQL with handle
        queries = [
            {"query": f'{{ seller(nickname: "{handle}") {{ id products(first: 10) {{ edges {{ node {{ id }} }} }} }} }}'},
            {"query": f'{{ seller(slug: "{handle}") {{ id products(first: 10) {{ edges {{ node {{ id }} }} }} }} }}'},
            {"query": f'{{ search(term: "", seller: "{handle}") {{ products(first: 10) {{ edges {{ node {{ id }} }} }} }} }}'},
            {"query": '{ __schema { queryType { fields { name } } } }'},
        ]
        for i, q in enumerate(queries):
            r = await client.post(SEARCH, json=q)
            print(f"\nGraphQL query {i+1} -> {r.status_code}")
            if r.status_code == 200:
                print(r.text[:500])

        # 5. Try search API
        r = await client.get(BASE + f"/api/products/search", params={"seller": handle, "page": "1"})
        print(f"\n/api/products/search -> {r.status_code}")
        if r.status_code == 200:
            print(r.text[:500])


asyncio.run(test())
