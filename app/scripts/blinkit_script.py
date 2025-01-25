import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

    # Initialize the WebDriver with Chrome options
    logging.info("Initializing the WebDriver with user profile.")
    chrome_options = webdriver.ChromeOptions()
    # Use absolute path without escaping
    user_data_dir = os.path.join(os.path.expanduser('~'), "Library", "Application Support", "Google", "Chrome")
    chrome_options.add_argument(f'user-data-dir={user_data_dir}')
    chrome_options.add_argument('profile-directory=Profile 9')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    try:
        # Step 1: Open Swiggy's website
        log_and_execute("Opening Swiggy's website.", driver.get, "https://blinkit.com/s/")
        time.sleep(5)

        search_box = log_and_execute(
            "Finding the search input box.",
            driver.find_element,
            By.XPATH,
            "//input[contains(@placeholder, 'Search')]"
        )
        log_and_execute("Typing 'Pizza' into the search box.", search_box.send_keys, "Bread")
        time.sleep(2)
        log_and_execute("Pressing ENTER to search.", search_box.send_keys, Keys.ENTER)
        time.sleep(5)


        # Step 5: Add the first item to the cart
        add_to_cart_button = log_and_execute(
            "Finding the 'Add to Cart' button.",
            driver.find_element,
            By.XPATH,
            '(//div[contains(@class, "AddToCart")])[1]'
        )
        
        # Scroll to bring button into view, but offset to avoid header overlap
        driver.execute_script("""
            arguments[0].scrollIntoView({block: 'center'});
            window.scrollBy(0, -100);  // Scroll up to avoid header overlap
            return true;
        """, add_to_cart_button)
        
        time.sleep(2)  # Wait for scroll to complete
        
        # Try to click using JavaScript if normal click is intercepted
        try:
            add_to_cart_button.click()
        except:
            driver.execute_script("arguments[0].click();", add_to_cart_button)
        
        time.sleep(3)

        # Step 6: Proceed to the cart
        cart_button = log_and_execute(
            "Finding the 'View Cart' button.",
            WebDriverWait(driver, 10).until,
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class, 'CartButton') or contains(@class, 'cart-button') or contains(text(), 'Cart')]"
            ))
        )
        
        # Debug: Print cart button details
        print("Cart button HTML:", cart_button.get_attribute('outerHTML'))
        print("Cart button classes:", cart_button.get_attribute('class'))
        
        # Highlight the button to verify
        driver.execute_script("arguments[0].style.border='3px solid red'", cart_button)
        time.sleep(2)
        
        log_and_execute("Clicking the cart button.", cart_button.click)
        time.sleep(3)

        # Step 7: Checkout
        checkout_button = log_and_execute(
            "Finding the 'Checkout' button.",
            driver.find_element,
            By.XPATH,
            '//div[contains(@class, "CheckoutStrip__StripContainer")]'
        )
        
        # Debug info
        print("Checkout button HTML:", checkout_button.get_attribute('outerHTML'))
        print("Checkout button classes:", checkout_button.get_attribute('class'))
        
        # Highlight to verify
        driver.execute_script("arguments[0].style.border='3px solid red'", checkout_button)
        time.sleep(2)
        
        log_and_execute("Clicking the 'Checkout' button.", checkout_button.click)
        time.sleep(3)

        # Step 8: Select Address
        address_button = log_and_execute(
            "Finding the 'Select Address' button.",
            driver.find_element,
            By.XPATH,
            '(//div[contains(@class, "AddressList__AddressLabel")])[1]'
        )
        driver.execute_script("arguments[0].style.border='3px solid red'", address_button)
        time.sleep(2)

        log_and_execute("Clicking the 'Select Address' button.", address_button.click)
        time.sleep(3)

        logging.info("Automation completed successfully. Please complete the payment manually.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    finally:
        logging.info("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()