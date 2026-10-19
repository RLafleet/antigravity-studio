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

        print("1. Navigating to arena_3d.html...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/arena_3d.html", wait_until="networkidle")
        
        print("2. Waiting 4 seconds for model loading...")
        await asyncio.sleep(4.0)

        # Check initial state
        initial_phase = await page.evaluate("() => document.getElementById('boss-phase-badge')?.innerText")
        initial_hp = await page.evaluate("() => document.getElementById('hp-text')?.innerText")
        print(f"Initial Phase: {initial_phase}, HP: {initial_hp}")

        # Capture Phase 1: Confidence
        await page.screenshot(path="confidence_phase.png")
        print("Captured confidence_phase.png")

        # Deliver punches until Panic Phase (<40% HP, so <= 48 HP)
        print("3. Delivering punches to enter Tension and Panic phases...")
        for i in range(5):
            await page.evaluate("window.triggerPunch()")
            await asyncio.sleep(0.3)

        mid_phase = await page.evaluate("() => document.getElementById('boss-phase-badge')?.innerText")
        mid_hp = await page.evaluate("() => document.getElementById('hp-text')?.innerText")
        print(f"Mid Phase: {mid_phase}, HP: {mid_hp}")

        # More punches to reach Panic (<48 HP)
        for i in range(4):
            await page.evaluate("window.triggerPunch()")
            await asyncio.sleep(0.3)

        panic_phase = await page.evaluate("() => document.getElementById('boss-phase-badge')?.innerText")
        panic_hp = await page.evaluate("() => document.getElementById('hp-text')?.innerText")
        print(f"Panic Phase: {panic_phase}, HP: {panic_hp}")

        # Capture Phase 3: Panic
        await page.screenshot(path="panic_phase.png")
        print("Captured panic_phase.png")

        # Deliver final punches for Knockout
        print("4. Delivering knockout blow...")
        for i in range(6):
            await page.evaluate("window.triggerPunch()")
            await asyncio.sleep(0.3)

        await asyncio.sleep(1.0)
        ko_visible = await page.evaluate("() => document.getElementById('ko-banner')?.style.opacity")
        ko_hp = await page.evaluate("() => document.getElementById('hp-text')?.innerText")
        print(f"KO Banner Opacity: {ko_visible}, Final HP: {ko_hp}")

        # Capture Knockout
        await page.screenshot(path="knockout_phase.png")
        print("Captured knockout_phase.png")

        await browser.close()
        print(f"Test finished. Errors caught: {len(errors)}")
        if errors:
            print("Errors:", errors)

if __name__ == "__main__":
    asyncio.run(run())
