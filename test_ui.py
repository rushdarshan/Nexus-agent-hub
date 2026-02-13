
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("🚀 Launching Browser for UI Test...")
        # Launch headless for speed, or headed to see it execution
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "http://localhost:5173"
        print(f"🌐 Navigating to {url}...")
        try:
            await page.goto(url, timeout=10000)
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            await browser.close()
            return

        # Check title/content
        title = await page.title()
        print(f"📄 Page Title: {title}")
        
        # Take initial screenshot
        await page.screenshot(path="dashboard_initial.png")
        print("📸 Initial screenshot saved to dashboard_initial.png")

        # Interact: Find input and button
        # Based on GodMode.tsx, look for input class or placeholder
        try:
            # Type goal
            # Looking for input with placeholder "Found a bug? Fix it?" or similar from GodMode.tsx
            # Or class "input-box"
            input_selector = "input[type='text']" 
            await page.wait_for_selector(input_selector, timeout=5000)
            await page.fill(input_selector, "Test Agent via Playwright Script")
            print("⌨️ Typed goal into input box")
            
            # Click Update Goal or Single Agent
            # Looking for button text
            await page.click("text=SINGLE AGENT") # Or "UPDATE GOAL"
            print("🖱️ Clicked 'SINGLE AGENT' button")
            
            # Wait for some status change
            await asyncio.sleep(5)
            
            # Take Result Screenshot
            await page.screenshot(path="dashboard_result.png")
            print("📸 Result screenshot saved to dashboard_result.png")
            
        except Exception as e:
            print(f"⚠️ Interaction failed (Element not found?): {e}")
            # Save debug screenshot
            await page.screenshot(path="dashboard_error.png")

        await browser.close()
        print("✅ UI Test Completed.")

if __name__ == "__main__":
    asyncio.run(run())
