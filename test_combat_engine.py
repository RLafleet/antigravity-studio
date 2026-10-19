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
        page = await browser.new_page(viewport={'width': 1024, 'height': 850})
        
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        print("Navigating to arena_3d.html...")
        await page.goto("http://127.0.0.1:48123/assets/monsters/goblin_puppet/arena_3d.html", wait_until="networkidle")
        await asyncio.sleep(4.0)

        # 1. Capture base combat state
        await page.screenshot(path="combat_dual_bars.png")
        print("Captured combat_dual_bars.png")

        # 2. Test Dodge Left
        print("Testing Dodge Left...")
        await page.keyboard.press("KeyA")
        await asyncio.sleep(0.15)
        await page.screenshot(path="dodge_left_state.png")
        print("Captured dodge_left_state.png")
        await asyncio.sleep(0.5)

        # 3. Test Block (hold S)
        print("Testing Block...")
        await page.keyboard.down("KeyS")
        await asyncio.sleep(0.2)
        await page.screenshot(path="block_guard_state.png")
        print("Captured block_guard_state.png")
        await page.keyboard.up("KeyS")
        await asyncio.sleep(0.3)

        # 4. Test Punching
        print("Testing punches...")
        await page.keyboard.press("Space")
        await asyncio.sleep(0.15)
        await page.keyboard.press("Space")
        await asyncio.sleep(0.4)

        # 5. Test Shop Modal
        print("Testing Shop Modal...")
        await page.evaluate("window.openShopModal()")
        await asyncio.sleep(0.5)
        await page.screenshot(path="shop_modal_state.png")
        print("Captured shop_modal_state.png")

        # 6. Test Upgrade purchase in Shop
        print("Buying Power upgrade...")
        await page.evaluate("window.buyUpgrade('power', 45)")
        await asyncio.sleep(0.3)
        await page.screenshot(path="shop_after_upgrade.png")
        print("Captured shop_after_upgrade.png")
        await page.evaluate("window.closeShopModal()")
        await asyncio.sleep(0.5)

        # 7. Wait for Boss AI attack and telegraph
        print("Waiting for Boss AI attack...")
        await asyncio.sleep(3.5)
        await page.screenshot(path="boss_attack_loop.png")
        print("Captured boss_attack_loop.png")

        await browser.close()
        print("COMBAT ENGINE VERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(run())
