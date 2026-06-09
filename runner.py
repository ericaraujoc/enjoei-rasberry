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
_GLOBAL_TIMEOUT = 90


async def _run_megafonar(loja_url: str, cookie_value: str) -> int:
    """
    Opens the store page and clicks all available megafonar buttons.
    Returns the number of boosts performed, or -1 if not logged in.
    Raises on unrecoverable errors.
    """
    try:
        pw = await async_playwright().start()
    except Exception as e:
        logger.error(f"Failed to start Playwright: {e}")
        raise RuntimeError(f"Playwright start failed: {e}") from e

    try:
        browser = await pw.chromium.launch(headless=True)
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        await pw.stop()
        raise RuntimeError(f"Browser launch failed: {e}") from e

    try:
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
            return 0

        logged_in = any([
            await page.query_selector("[data-testid='user-menu']"),
            await page.query_selector("[class*='user-avatar']"),
            await page.query_selector("a[href*='logout']"),
        ])
        if not logged_in:
            logger.warning(f"Not logged in — {loja_url}")
            return -1

        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.8)

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

        return count
    finally:
        await browser.close()
        await pw.stop()


async def executar_megafonar(loja_url: str, cookie_value: str) -> int:
    """Wrapper with global timeout to prevent infinite hangs."""
    return await asyncio.wait_for(
        _run_megafonar(loja_url, cookie_value),
        timeout=_GLOBAL_TIMEOUT,
    )
