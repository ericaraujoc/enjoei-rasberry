import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

_COOKIE_NAME = "_website_session_7"
_DOMAIN = "www.enjoei.com.br"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def executar_megafonar(loja_url: str, cookie_value: str) -> int:
    """
    Opens the store page and clicks all available megafonar buttons.
    Returns the number of boosts performed, or -1 if not logged in.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)

        await context.add_cookies([{
            "name": _COOKIE_NAME,
            "value": cookie_value,
            "domain": _DOMAIN,
            "path": "/",
        }])

        page = await context.new_page()

        try:
            await page.goto(loja_url, wait_until="domcontentloaded", timeout=30_000)
        except PWTimeout:
            logger.error(f"Timeout loading {loja_url}")
            await browser.close()
            return 0

        # Verify login
        logged_in = any([
            await page.query_selector("[data-testid='user-menu']"),
            await page.query_selector("[class*='user-avatar']"),
            await page.query_selector("a[href*='logout']"),
        ])
        if not logged_in:
            logger.warning(f"Not logged in — {loja_url}")
            await browser.close()
            return -1

        # Scroll to lazy-load all product cards
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.8)

        # Click every available megafonar button
        buttons = await page.query_selector_all("button")
        count = 0
        for btn in buttons:
            try:
                text = (await btn.inner_text()).lower()
                if "megafonar" in text and "agora" not in text:
                    await btn.click()
                    count += 1
                    await asyncio.sleep(2)
            except Exception:
                continue

        await browser.close()
        return count
