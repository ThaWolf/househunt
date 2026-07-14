"""Shared Playwright browser helpers for live portal scrapers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

_RATE_LOCK = asyncio.Lock()
_LAST_REQUEST_AT: float = 0.0
_MIN_INTERVAL_SECONDS = 3.0

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class BrowserFetchError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


async def _rate_limit() -> None:
    global _LAST_REQUEST_AT
    async with _RATE_LOCK:
        now = asyncio.get_event_loop().time()
        wait = _MIN_INTERVAL_SECONDS - (now - _LAST_REQUEST_AT)
        if wait > 0:
            await asyncio.sleep(wait)
        _LAST_REQUEST_AT = asyncio.get_event_loop().time()


def detect_bot_wall(url: str, html: str, status: int | None) -> bool:
    u = (url or "").lower()
    h = html or ""
    if "captcha" in u or "/challenge" in u:
        return True
    if "Just a moment" in h[:4000]:
        return True
    if "cf-browser-verification" in h[:8000]:
        return True
    if status in (403, 429):
        return True
    return False


@asynccontextmanager
async def browser_page(*, timeout_ms: int = 45000) -> AsyncIterator[Any]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        raise BrowserFetchError("network", "playwright not installed") from exc

    await _rate_limit()
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent=UA,
        locale="es-AR",
        viewport={"width": 1440, "height": 900},
    )
    page = await context.new_page()
    page.set_default_timeout(timeout_ms)
    try:
        yield page
    finally:
        await context.close()
        await browser.close()
        await pw.stop()


async def goto_html(
    page: Any,
    url: str,
    *,
    wait_bot_clear_seconds: float = 12.0,
) -> tuple[str, str, int | None]:
    """Navigate and return (final_url, html, status). Raises BrowserFetchError."""
    try:
        resp = await page.goto(url, wait_until="domcontentloaded")
        status = resp.status if resp else None
    except Exception as exc:  # noqa: BLE001
        raise BrowserFetchError("network", f"navigation failed: {type(exc).__name__}") from exc

    # Cloudflare / soft wait
    deadline = asyncio.get_event_loop().time() + wait_bot_clear_seconds
    html = await page.content()
    final_url = page.url
    while detect_bot_wall(final_url, html, status) and asyncio.get_event_loop().time() < deadline:
        await page.wait_for_timeout(1500)
        html = await page.content()
        final_url = page.url
        if "Just a moment" not in html:
            break

    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    html = await page.content()
    final_url = page.url
    if detect_bot_wall(final_url, html, status):
        raise BrowserFetchError("bot_wall", f"Portal bot wall at {final_url}")
    if status == 429:
        raise BrowserFetchError("rate_limit", "HTTP 429 from portal")
    return final_url, html, status
