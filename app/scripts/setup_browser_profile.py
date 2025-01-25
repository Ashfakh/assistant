import asyncio
from pathlib import Path
import argparse
from playwright.async_api import async_playwright

async def setup_profile():
    parser = argparse.ArgumentParser(description='Setup Playwright browser profile')
    parser.add_argument('--user-data-dir', type=str, 
                      default=str(Path.home() / '.playwright-profile'),
                      help='Directory for persistent browser profile')
    args = parser.parse_args()

    print(f"Setting up browser profile in: {args.user_data_dir}")
    print("Please log in to the websites you want to use.")
    print("The browser will stay open until you press Enter in this terminal.")

    async with async_playwright() as p:
        # Launch persistent context
        context = await p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            headless=False,
        )
        
        # Open a new page
        page = await context.new_page()
        await page.goto("https://www.google.com")
        
        # Wait for user input before closing
        input("Press Enter to close the browser and save the profile...")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(setup_profile())