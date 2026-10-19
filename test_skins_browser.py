import asyncio
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--use-gl=angle',
                '--use-angle=swiftshader',
                '--enable-webgl',
                '--ignore-gpu-blocklist'
            ]
        )
        page = await browser.new_page(viewport={'width': 1024, 'height': 800})
        
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        print("Navigating to arena_3d.html...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/arena_3d.html", wait_until="networkidle")
        
        # Wait 4 seconds for model loading and initial skin application
        print("Waiting 4 seconds...")
        await asyncio.sleep(4.0)

        # Check loading-msg text
        msg_text = await page.evaluate("() => document.getElementById('loading-msg')?.innerText")
        print(f"Loading Msg: {msg_text}")

        # Check if monsterRoot is loaded
        is_loaded = await page.evaluate("() => !!window.switchSkin")
        print(f"switchSkin available: {is_loaded}")

        # Take screenshot
        await page.screenshot(path="arena_state.png")
        print("Captured arena_state.png")

        # Switch to Toxic
        print("Switching skin to toxic...")
        await page.evaluate("window.switchSkin('toxic')")
        await asyncio.sleep(1.0)
        await page.screenshot(path="toxic_state.png")
        print("Captured toxic_state.png")

        # Switch to Frost
        print("Switching skin to frost...")
        await page.evaluate("window.switchSkin('frost')")
        await asyncio.sleep(1.0)
        await page.screenshot(path="frost_state.png")
        print("Captured frost_state.png")

        # Switch to Original Stone
        print("Switching skin to original...")
        await page.evaluate("window.switchSkin('original')")
        await asyncio.sleep(1.0)
        await page.screenshot(path="stone_state.png")
        print("Captured stone_state.png")

        # Switch back to Lava and punch
        print("Switching skin to lava and punching...")
        await page.evaluate("window.switchSkin('lava')")
        await asyncio.sleep(0.5)
        await page.evaluate("window.triggerPunch('right')")
        await asyncio.sleep(0.12)
        await page.screenshot(path="punch_state.png")
        print("Captured punch_state.png")

        await browser.close()
        print("ALL TESTS COMPLETE SUCCESSFULLY")

if __name__ == "__main__":
    asyncio.run(run())
