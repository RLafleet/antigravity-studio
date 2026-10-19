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
        page = await browser.new_page(viewport={'width': 1024, 'height': 768})
        
        errors = []
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("1. Loading vrm_preview.html with combat animations...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/vrm_preview.html", wait_until="networkidle")
        
        # Wait up to 15 seconds for combat readiness
        for _ in range(30):
            ready = await page.evaluate("window._vrmCombatReady === true")
            if ready:
                break
            await asyncio.sleep(0.5)

        print("2. Capturing Idle stance screenshot...")
        await asyncio.sleep(1.2)
        await page.screenshot(path="vrm_idle_pose.png")
        print("Captured vrm_idle_pose.png")

        print("3. Testing HitReact...")
        await page.evaluate("window.playAnim('HitReact')")
        await asyncio.sleep(0.12)
        await page.screenshot(path="vrm_hit_pose.png")
        print("Captured vrm_hit_pose.png")

        print("4. Testing AttackHook...")
        await page.evaluate("window.playAnim('AttackHook')")
        await asyncio.sleep(0.25)
        await page.screenshot(path="vrm_attack_pose.png")
        print("Captured vrm_attack_pose.png")

        print(f"Total page errors: {len(errors)}")
        if errors:
            print("Errors:", errors)

        await browser.close()
        print("Test finished successfully.")

if __name__ == "__main__":
    asyncio.run(run())
