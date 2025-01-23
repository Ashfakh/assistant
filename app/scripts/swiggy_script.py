import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time

def log_and_execute(step_description, action, *args, **kwargs):
    try:
        logging.info(f"Step: {step_description}")
        return action(*args, **kwargs)
    except Exception as e:
        logging.error(f"Failed at step: {step_description}. Error: {e}")
        raise

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Initialize the WebDriver
    logging.info("Initializing the WebDriver.")
    driver = webdriver.Chrome()  # or webdriver.Firefox() for Firefox users
    driver.maximize_window()

    try:
        # Step 1: Open Swiggy's website
        log_and_execute("Opening Swiggy's website.", driver.get, "https://www.swiggy.com/")
        time.sleep(2)

        # Step 2: Enter location
        location_input = log_and_execute(
            "Finding the location input box.",
            driver.find_element,
            By.ID,
            "location"
        )
        log_and_execute("Clicking on the location input box.", location_input.click)
        log_and_execute(
            "Typing location 'Koramangala, Bangalore'.",
            location_input.send_keys,
            "Koramangala, Bangalore"  # Replace with your location
        )
        time.sleep(2)
        log_and_execute("Pressing ENTER to confirm the location.", location_input.send_keys, Keys.ENTER)
        time.sleep(5)

        # Step 3: Search for an item
        search_box_button = log_and_execute(
            "Finding the search input box.",
            driver.find_element,
             By.XPATH,
            '//div[contains(text(), "Search for restaurant, item or more")]'
        )
        log_and_execute("Clicking on the search input box.", search_box_button.click)
        time.sleep(5)
        search_box = log_and_execute(
            "Finding the search input box.",
            driver.find_element,
             By.XPATH,
             "//input[@placeholder='Search for restaurants and food']"
        )
        log_and_execute("Typing 'Pizza' into the search box.", search_box.send_keys, "Pizza")
        time.sleep(5)
        log_and_execute("Pressing ENTER to search.", search_box.send_keys, Keys.ENTER)
        time.sleep(5)

        # Step 4: Select the first restaurant/item from the list
        first_result = log_and_execute(
            "Finding the first search result.",
            driver.find_element,
            By.XPATH,
            '(//div[contains(@class, "styles_restaurantName__")])[1]'
        )
        log_and_execute("Clicking on the first search result.", first_result.click)
        time.sleep(5)

        # Step 5: Add the first item to the cart
        add_to_cart_button = log_and_execute(
            "Finding the 'Add to Cart' button.",
            driver.find_element,
            By.XPATH,
            '(//div[contains(@class, "styles_addBtn")])[1]'
        )
        log_and_execute("Clicking the 'Add to Cart' button.", add_to_cart_button.click)
        time.sleep(3)

        # Step 6: Proceed to the cart
        cart_button = log_and_execute(
            "Finding the 'View Cart' button.",
            driver.find_element,
            By.XPATH,
            '//div[contains(text(), "View Cart")]'
        )
        log_and_execute("Clicking the 'View Cart' button.", cart_button.click)
        time.sleep(3)

        # Step 7: Checkout
        checkout_button = log_and_execute(
            "Finding the 'Checkout' button.",
            driver.find_element,
            By.XPATH,
            '//div[contains(text(), "Checkout")]'
        )
        log_and_execute("Clicking the 'Checkout' button.", checkout_button.click)
        time.sleep(3)

        logging.info("Automation completed successfully. Please complete the payment manually.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    finally:
        logging.info("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()