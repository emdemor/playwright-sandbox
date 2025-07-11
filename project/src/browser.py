import asyncio
import random
from typing import Literal

from fake_useragent import UserAgent

from .config import browser_settings
from .proxies import get_masked_proxy

ua = UserAgent()


async def set_chromium(playwright, headless=True, proxy=None):
    browser_opts = dict(headless=headless)

    if proxy:
        print(f"using proxy {get_masked_proxy(proxy)}")
        browser_opts.update(dict(proxy=proxy))

    return await playwright.chromium.launch(
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
        **browser_opts,
    )


async def set_firefox(playwright, headless=True, proxy=None):
    browser_opts = dict(headless=headless)

    if proxy:
        print(f"using proxy {get_masked_proxy(proxy)}")
        browser_opts.update(dict(proxy=proxy))

    return await playwright.firefox.launch(
        firefox_user_prefs={
            "dom.webdriver.enabled": False,
            "privacy.resistFingerprinting": False,
            "browser.cache.disk.enable": True,
            "browser.cache.memory.enable": True,
        },
        args=["--disable-dev-shm-usage", "--no-sandbox"],
        **browser_opts,
    )


async def set_browser(
    playwright,
    engine: Literal["firefox", "chromium", "random"],
    headless: bool = True,
    proxy=None,
):
    browser_opts = dict(headless=headless)

    if proxy:
        browser_opts.update(dict(proxy=proxy))

    if engine == "random":
        engine = random.choice(["chromium", "firefox"])

    match engine:
        case "firefox":
            return await set_firefox(playwright, **browser_opts)
        case "chromium":
            return await set_chromium(playwright, **browser_opts)
        case _:
            raise ValueError(f"Engine {engine} not recognized.")


async def set_context(browser):
    # Create a new browser context with random viewport size
    viewport_width = random.randint(*browser_settings.viewport_width_range)
    viewport_height = random.randint(*browser_settings.viewport_height_range)

    return await browser.new_context(
        user_agent=ua.random,
        viewport={"width": viewport_width, "height": viewport_height},
        locale=random.choice(browser_settings.locales),
        timezone_id=random.choice(browser_settings.timezones),
        permissions=["geolocation"],
        has_touch=random.choice([True, False]),
    )


async def set_page(context):
    page = await context.new_page()

    # Emulate human-like behavior by intercepting WebDriver calls
    await page.add_init_script(
        """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false
    });

    // Add plugins length
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // Overwrite the languages property
    Object.defineProperty(navigator, 'languages', {
        get: () => ['pt-BR', 'pt']
    });
    """
    )

    return page


async def do_movements(page):
    # Random scrolling behavior
    for _ in range(random.randint(*browser_settings.mouse_scroll_moves_range)):
        await page.mouse.wheel(
            0, random.randint(*browser_settings.mouse_scroll_wheel_moves_range)
        )
        await asyncio.sleep(
            random.uniform(*browser_settings.mouse_scroll_move_sleep_range)
        )

    # Random mouse movements
    for _ in range(random.randint(*browser_settings.mouse_translate_moves_range)):
        await page.mouse.move(
            random.randint(100, 1000 - 100),
            random.randint(100, 800 - 100),
            steps=random.randint(1, 4),
        )
        await asyncio.sleep(random.uniform(0.05, 0.1))
