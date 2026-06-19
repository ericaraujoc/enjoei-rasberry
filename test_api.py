import asyncio
import httpx
import json
import re

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
        # 1. Get store JSON - should have seller_id
        r = await client.get(f"{BASE}/@{handle}.json")
        print(f"\n=== /@{handle}.json ===")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            try:
                store_data = r.json()
                print(f"Keys: {list(store_data.keys())[:20]}")
                seller_id = store_data.get("id") or store_data.get("seller_id") or store_data.get("user_id")
                print(f"Seller ID: {seller_id}")
                print(f"First 1000 chars: {r.text[:1000]}")
            except Exception as e:
                print(f"Not JSON: {r.text[:500]}")

        # 2. Parse minha-lojinha for product IDs
        r = await client.get(f"{BASE}/perfil/minha-lojinha")
        print(f"\n=== /perfil/minha-lojinha ===")
        print(f"Status: {r.status_code}, length: {len(r.text)}")
        ids = set()
        for m in re.findall(r'/p/[^"\s]*?-(\d{5,})', r.text):
            ids.add(m)
        for m in re.findall(r'product[_-]id["\s:=]+["\']?(\d{5,})', r.text, re.IGNORECASE):
            ids.add(m)
        for m in re.findall(r'/produtos/(\d{5,})', r.text):
            ids.add(m)
        print(f"Product IDs from regex: {len(ids)}")
        if ids:
            print(f"IDs: {list(ids)[:20]}")

        # Also try to find numeric IDs near "megafon" text
        megafone_context = re.findall(r'.{0,100}megafon.{0,100}', r.text, re.IGNORECASE)
        print(f"\nMegafone context found: {len(megafone_context)} matches")
        for ctx in megafone_context[:3]:
            print(f"  {ctx[:200]}")

        # 3. Try GraphQL with correct schema
        if seller_id:
            query = {
                "query": f'{{ seller(id: "{seller_id}") {{ search(products: {{term: ""}}) {{ products(first: 50) {{ edges {{ node {{ id }} }} }} }} }} }}'
            }
            r = await client.post(SEARCH, json=query)
            print(f"\n=== GraphQL with seller_id={seller_id} ===")
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text[:1000]}")

        # 4. Try introspecting the GraphQL schema
        query = {"query": '{ __schema { queryType { fields { name args { name type { name kind ofType { name } } } } } } }'}
        r = await client.post(SEARCH, json=query)
        print(f"\n=== GraphQL Schema ===")
        if r.status_code == 200:
            schema = r.json()
            if "data" in schema and schema["data"]:
                fields = schema["data"].get("__schema", {}).get("queryType", {}).get("fields", [])
                for f in fields:
                    args = [a["name"] for a in f.get("args", [])]
                    print(f"  {f['name']}({', '.join(args)})")


asyncio.run(test())
