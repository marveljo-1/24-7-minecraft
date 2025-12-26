import asyncio
import time
from playwright.async_api import async_playwright
import json
from pathlib import Path

COOKIE_FILE = Path("ptero_cookies.json")
SCRIPT_START = time.perf_counter()
SERVER_URL = "https://panel.freegamehost.xyz/server/7fbf24f4"
COOKIE = None

if COOKIE_FILE.exists():
    with COOKIE_FILE.open() as f:
        COOKIE = json.load(f)
if COOKIE:
    print("pterodactyl_session loaded!")
else:
    print("No cached pterodactyl_session found")
    
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        await context.add_cookies([COOKIE])
        await page.goto(SERVER_URL)
        # Click RENEW SERVER
        try:
            renew_btn = page.locator('//button[.//span[contains(.,"RENEW SERVER")]]')
            await renew_btn.wait_for(timeout=5000)
            await renew_btn.click()
            print("Renew button clicked")
            await asyncio.sleep(2)
        except:
            print(f"Renew button not found or already renewed")
            exit()

        try:
            turnstile = page.locator('div[data-tw="w-[150px] h-[140px]"]')
            await turnstile.wait_for(timeout=5000)
            box = await turnstile.bounding_box()
            offset_x = 36  # pixels from left of div
            offset_y = 47  # pixels from top of div

            click_x = box['x'] + offset_x
            click_y = box['y'] + offset_y

            await page.mouse.move(click_x, click_y, steps=20)
            await page.mouse.click(click_x, click_y)
            print("Turnstile clicked")
            await asyncio.sleep(2)
        except:
            print("Turnstile not found")

        # Extract only the pterodactyl_session cookie
        cookies = await context.cookies()
        ptero_cookie = next((c for c in cookies if c["name"] == "pterodactyl_session"), None)
        if ptero_cookie:
            with COOKIE_FILE.open("w") as f:
                json.dump(ptero_cookie, f)
            print("pterodactyl_session saved!")
        else:
            print("No pterodactyl_session found")

        runtime = time.perf_counter() - SCRIPT_START
        print(f"Total runtime: {runtime:.2f}s")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
