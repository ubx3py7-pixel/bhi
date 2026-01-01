import asyncio
from playwright.async_api import async_playwright

SESSION_ID = "79953061948%3AH0kSHXksRAcfeJ%3A9%3AAYjK4w3ejAVlQ-W-hHsT5WKR2FKd4UmxHDnHN9UP5w"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        await context.add_cookies([{
            "name": "sessionid",
            "value": SESSION_ID,
            "domain": ".instagram.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
        }])

        page = await context.new_page()

        # ✅ Go to Instagram
        await page.goto("https://www.instagram.com/", timeout=60000)

        # ✅ DO NOT use networkidle
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)  # allow UI to settle

        # ✅ Save session
        await context.storage_state(path="ig_session.json")
        print("✅ ig_session.json created successfully")

        await browser.close()

asyncio.run(main())
