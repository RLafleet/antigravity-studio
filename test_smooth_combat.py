import asyncio
import sys

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
        
        errors = []
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("1. Loading arena_3d.html...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/arena_3d.html", wait_until="networkidle")
        await asyncio.sleep(4.0)

        # Baseline screenshot
        await page.screenshot(path="smooth_idle.png")
        print("Captured smooth_idle.png")

        # Deliver 3 punches with delay and capture mid-reaction
        print("2. Punching...")
        await page.evaluate("window.triggerPunch('left')")
        await asyncio.sleep(0.12) # right on impact
        await page.screenshot(path="smooth_punch_impact.png")
        print("Captured smooth_punch_impact.png")

        # Wait for natural return to idle (HitReact clip duration is 0.333s)
        await asyncio.sleep(0.4)
        await page.screenshot(path="smooth_returned_idle.png")
        print("Captured smooth_returned_idle.png")

        # Check console errors
        print(f"Total errors: {len(errors)}")
        if errors:
            print("Errors:", errors)

        await browser.close()
        print("Test finished successfully.")

if __name__ == "__main__":
    asyncio.run(run())
