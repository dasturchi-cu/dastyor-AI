import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Testing Playwright...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content("<h1>Hello Playwright</h1>")
            pdf = await page.pdf()
            print(f"✅ Success! PDF generated: {len(pdf)} bytes")
            await browser.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
