from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

def extract_price_from_text(text):
    price_patterns = [
        r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
        r'PKR\s*([\d,]+(?:\.\d{2})?)',
        r'([\d,]+(?:\.\d{2})?)'
    ]
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                clean_price = re.sub(r'[^\d.]', '', str(match))
                if clean_price and float(clean_price) > 0:
                    return float(clean_price)
    return None

def debug_metro_price(url):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        time.sleep(5)  # Wait for JS to render
        price_candidates = []
        # Find all elements with 'price' in class name
        price_elements = driver.find_elements(By.XPATH, '//*[contains(@class, "price")]')
        for elem in price_elements:
            text = elem.text.strip()
            price = extract_price_from_text(text)
            if price:
                price_candidates.append(price)
        # As a fallback, also check all elements for 'Rs' or 'PKR'
        if not price_candidates:
            all_elements = driver.find_elements(By.XPATH, '//*')
            for elem in all_elements:
                text = elem.text.strip()
                price = extract_price_from_text(text)
                if price:
                    price_candidates.append(price)
        if price_candidates:
            lowest = min(price_candidates)
            print(f"[DEBUG] Metro lowest price found: {lowest}")
            print(f"Metro product price: Rs. {lowest:.2f}")
        else:
            print("[DEBUG] No valid price found on Metro page.")
    finally:
        driver.quit()

if __name__ == "__main__":
    url = "https://www.metro-online.pk/detail/frozen-food/frozen-ready-to-cook/parathas/dawn-paratha-plain-5pcs/12624312?categoryName=Search"
    debug_metro_price(url) 