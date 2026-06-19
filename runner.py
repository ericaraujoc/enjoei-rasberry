import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_COOKIE_NAME = "_website_session_7"
_BASE_URL = "https://www.enjoei.com.br"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_GLOBAL_TIMEOUT = 90


async def _get_csrf_token(client: httpx.AsyncClient) -> str | None:
    resp = await client.get(f"{_BASE_URL}/api/session/csrf_meta.json", params={"version": "v1"})
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("token")


async def _get_product_ids(client: httpx.AsyncClient, store_url: str) -> list[int]:
    resp = await client.get(store_url)
    if resp.status_code != 200:
        return []

    ids: set[int] = set()

    for match in re.findall(r'/p/[^"\'\s]*?-(\d{5,})', resp.text):
        ids.add(int(match))

    for match in re.findall(r'product_id["\s:=]+(\d{5,})', resp.text, re.IGNORECASE):
        ids.add(int(match))

    for match in re.findall(r'"id"\s*:\s*(\d{5,})', resp.text):
        ids.add(int(match))

    for match in re.findall(r'/produtos/(\d{5,})', resp.text):
        ids.add(int(match))

    return list(ids)


async def _get_boostable_products(client: httpx.AsyncClient, product_ids: list[int]) -> list[int]:
    if not product_ids:
        return []

    boostable: list[int] = []
    batch_size = 20
    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i:i + batch_size]
        ids_str = ",".join(str(pid) for pid in batch)
        resp = await client.get(
            f"{_BASE_URL}/api/megaphones/v2",
            params={"product_ids": ids_str, "version": "v2"},
        )
        if resp.status_code != 200:
            logger.warning(f"Megaphones API returned {resp.status_code}")
            continue
        data = resp.json()
        for product in data.get("products", []):
            if product.get("delay", 1) == 0:
                boostable.append(product["product_id"])

    return boostable


async def _boost_product(client: httpx.AsyncClient, product_id: int, csrf_token: str) -> bool:
    resp = await client.post(
        f"{_BASE_URL}/api/megaphones",
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf_token,
        },
        json={
            "version": "v2",
            "product_id": product_id,
        },
    )
    if resp.status_code == 200:
        logger.info(f"Boosted product {product_id}")
        return True
    logger.warning(f"Failed to boost {product_id}: {resp.status_code}")
    return False


async def _run_megafonar(store_url: str, cookie_value: str) -> int:
    async with httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        cookies={_COOKIE_NAME: cookie_value},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        csrf_token = await _get_csrf_token(client)
        if not csrf_token:
            logger.warning("Failed to get CSRF token — cookie expired?")
            return -1

        product_ids = await _get_product_ids(client, store_url)
        if not product_ids:
            logger.warning(f"No products found on {store_url}")
            return 0

        logger.info(f"Found {len(product_ids)} products, checking boost eligibility...")

        boostable = await _get_boostable_products(client, product_ids)
        if not boostable:
            logger.info("No products ready to boost (all on cooldown)")
            return 0

        logger.info(f"{len(boostable)} products ready to boost")

        count = 0
        for pid in boostable:
            if await _boost_product(client, pid, csrf_token):
                count += 1
                await asyncio.sleep(1.5)

        return count


async def executar_megafonar(store_url: str, cookie_value: str) -> int:
    return await asyncio.wait_for(
        _run_megafonar(store_url, cookie_value),
        timeout=_GLOBAL_TIMEOUT,
    )
