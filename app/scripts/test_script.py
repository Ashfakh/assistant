import structlog
import os
import logging
from selenium import webdriver

from app.browser.gpt_selenium_agent import GPTSeleniumAgent


def main():
    instructions = """Go to https://www.swiggy.com/search
Find the search div box with text Search.
Click on the search div box.
Wait for 5 seconds
Type in "Dosa" in the Search bar and press enter.
Wait for 5 Seconds
Find the first div that contains the text "Add".
Click on the div.
wait for 5 seconds
FInd the span that contains the text "Cart"
Click on the span.
Wait for 10 seconds."""
    # Initialize the WebDriver with Chrome options
    logging.info("Initializing the WebDriver with user profile.")
    # Initialize the WebDriver with Chrome options
    logging.info("Initializing the WebDriver with user profile.")
    chrome_options = webdriver.ChromeOptions()
    # Use absolute path without escaping
    user_data_dir = os.path.join(os.path.expanduser('~'), "Library", "Application Support", "Google", "Chrome")
    chrome_options.add_argument(f'user-data-dir={user_data_dir}')
    chrome_options.add_argument('profile-directory=Profile 9')
    # Specify the path to chromedriver executable
    chromedriver_path = "/opt/homebrew/bin/chromedriver"  # Adjust this path according to your system
    agent = GPTSeleniumAgent(
        instructions, 
        chromedriver_path=chromedriver_path,
        user_data_dir=user_data_dir,
        retry=True
    )
    agent.run()

if __name__ == "__main__":
    main()