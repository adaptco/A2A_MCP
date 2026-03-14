from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        # 1. Hero Mode
        print("Navigating to Hero Mode...")
        page.goto("http://localhost:3000")
        page.wait_for_selector("text=METADATA", timeout=10000)
        page.screenshot(path="hero_mode.png")
        print("Hero Mode screenshot saved.")

        # 2. Race Mode
        print("Switching to Race Mode...")
        page.click("text=RACE PROTOTYPE")
        # Wait for HUD element
        page.wait_for_selector("text=POS 1/6", timeout=10000)
        # Give Three.js a moment to render
        page.wait_for_timeout(2000)
        page.screenshot(path="race_mode.png")
        print("Race Mode screenshot saved.")

    except Exception as e:
        print(f"Error: {e}")
        # Take a screenshot if something fails to help debug
        try:
            page.screenshot(path="error_state.png")
        finally:
            raise

    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
