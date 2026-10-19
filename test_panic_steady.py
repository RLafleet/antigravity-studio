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
        
        print("Navigating to arena_3d.html...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/arena_3d.html", wait_until="networkidle")
        await asyncio.sleep(4.0)

        # Deliver 6 timed punches (each ~15 dmg, 6*15 = 90 dmg, bringing HP from 120 to ~30 HP which is Panic Phase)
        for i in range(6):
            await page.evaluate("window.triggerPunch()")
            await asyncio.sleep(0.35)

        # Wait 0.5s for hit reactions to settle so monster is in panic idle
        await asyncio.sleep(0.6)

        phase = await page.evaluate("() => document.getElementById('boss-phase-badge')?.innerText")
        hp_val = await page.evaluate("() => document.getElementById('hp-text')?.innerText")
        print(f"Panic State: Phase={phase}, HP={hp_val}")

        await page.screenshot(path="panic_phase_steady.png")
        print("Captured panic_phase_steady.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
