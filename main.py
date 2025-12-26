import asyncio
import time
import cv2
import numpy as np
from playwright.async_api import async_playwright
from undetected_playwright import Tarnished

SCRIPT_START = time.perf_counter()
AUTH_URL = "https://www.freemchost.com/auth"
SERVER_URL = "https://www.freemchost.com/server?id=602014782"
COOKIE = {
    "name": "PHPSESSID",
    "value": "gol1sc9r9up2v2lhog5duh3bg2",
    "domain": "www.freemchost.com",
    "path": "/",
}

# Light and dark templates
TEMPLATES = ["checkbox_light.png", "checkbox_dark.png"]
THRESHOLD = 0.76

# Preload templates and convert to grayscale
templates = []
for path in TEMPLATES:
    tpl = cv2.imread(path)
    if tpl is None:
        raise RuntimeError(f"{path} not found")
    tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    h, w = tpl_gray.shape
    templates.append((tpl_gray, w, h))

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-backgrounding-occluded-windows",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = await browser.new_context(viewport=None)
        Tarnished.apply_stealth(context)

        page = await context.new_page()
        await page.goto(AUTH_URL)
        await context.add_cookies([COOKIE])

        await page.goto(SERVER_URL)
        dismiss_button = page.locator('button:has-text("Not Now")')
        count = await dismiss_button.count()
        if count > 0:
            for i in range(count):
                btn = dismiss_button.nth(i)
                if await btn.is_visible():
                    await btn.click()
                    break
        else:
            print("No dismiss button found")

        start_session = page.locator('button[name="start_session"]')
        if await start_session.count() > 0 and await start_session.is_visible():
            await start_session.click()
            await asyncio.sleep(2)
            await page.reload()
        else:
            print("Session already started")

        await asyncio.sleep(2)
        screenshot_bytes = await page.screenshot(full_page=True)
        sc = np.frombuffer(screenshot_bytes, np.uint8)
        sc = cv2.imdecode(sc, cv2.IMREAD_COLOR)
        sc_gray = cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY)

        # Try matching both templates
        detected = False
        for tpl_gray, w, h in templates:
            res = cv2.matchTemplate(sc_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= THRESHOLD:
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                await page.mouse.move(center_x, center_y, steps=25)
                await page.mouse.click(center_x, center_y)
                print(f"Turnstile detected and clicked using template {tpl_gray.shape}")
                detected = True
                break

        if not detected:
            print("Turnstile not detected in either light or dark mode")

        # Renew button handling
        renew_button = page.locator("#renewSessionBtn")
        renewFeedback = page.locator("#renewFeedback").first
        try:
            await renew_button.wait_for(state="visible", timeout=3000)
            await renew_button.click()
            await asyncio.sleep(1)
            await renewFeedback.wait_for(state="visible", timeout=3000)
            feedback_text = await renewFeedback.inner_text()
            print(f"Renew feedback: {feedback_text}")
        except Exception as e:
            print(f"Renew button not available: {e}")

        runtime = time.perf_counter() - SCRIPT_START
        print(f"Total runtime: {runtime:.2f}s")

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
