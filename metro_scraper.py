import csv
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import logging
from typing import List, Dict, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pymysql
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetroPriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.competitor_name = 'Metro'
        self.results = []
        
    def extract_price_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract price from HTML content for Metro
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # First, try to extract price from JSON data in script tags (Metro stores prices here)
        scripts = soup.find_all('script')
        for script in scripts:
            script_text = script.get_text()
            if script_text:
                # Look for JSON data containing price information
                if '"price"' in script_text and '"sell_price"' in script_text:
                    logger.info(f"Debug: Found Metro JSON data with prices")
                    # Extract price from JSON
                    price_match = re.search(r'"price":(\d+(?:\.\d+)?)', script_text)
                    sell_price_match = re.search(r'"sell_price":(\d+(?:\.\d+)?)', script_text)
                    
                    if sell_price_match:
                        price = sell_price_match.group(1)
                        logger.info(f"Debug: Found Metro sell_price: {price}")
                        if self.is_valid_price(price):
                            return self.format_price(price)
                    
                    if price_match:
                        price = price_match.group(1)
                        logger.info(f"Debug: Found Metro price: {price}")
                        if self.is_valid_price(price):
                            return self.format_price(price)
        
        # Use the specific Metro price selector path
        price_selector = "#__next > div > div.main-container > div > div.CategoryGrid_product_details_container_without_imageCarousel__xOYB6 > div.CategoryGrid_product_details_description_container__OjSn3 > p.CategoryGrid_product_details_price__dNQQQ"
        price_tag = soup.select_one(price_selector)
        
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            logger.info(f"Debug: Found Metro price using specific selector: '{price_text}'")
            price = self.extract_price_from_text(price_text)
            if price and self.is_valid_price(price):
                logger.info(f"Debug: Found Metro price: {price}")
                return self.format_price(price)
        
        # Also try the shorter class name as fallback
        price_tag = soup.find("p", class_="CategoryGrid_product_details_price__dNQQQ")
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            logger.info(f"Debug: Found Metro price using class selector: '{price_text}'")
            price = self.extract_price_from_text(price_text)
            if price and self.is_valid_price(price):
                logger.info(f"Debug: Found Metro price: {price}")
                return self.format_price(price)
        
        # Fallback to other Metro selectors
        metro_price_selectors = [
            '.product-price', '.price-display', '.price-value',
            '.product-price-value', '.price-amount', '.product-amount',
            '.selling-price', '.offer-price', '.discount-price', '.final-price',
            '.price-box', '.price-container', '.product-price-box',
            '.price-wrapper', '.price-section', '.product-price-section',
            '.product-details-price', '.current-price', '.regular-price',
            '.product-price-display', '.price-text', '.price-label',
            '.price', '.amount', '.product-price',
            '[class*="price"]', '[class*="Price"]', '[class*="amount"]',
            '[class*="Amount"]', '[class*="cost"]', '[class*="Cost"]',
            '[data-price]', '[data-amount]', '[data-value]',
            '.cost', '.value', '.product-cost', '.product-value',
            '.product-details', '.product-info', '.product-summary',
            '.product-description', '.product-content'
        ]
        
        # Try to find price in specific Metro elements
        for selector in metro_price_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                # Skip very short or very long text
                if len(text) < 3 or len(text) > 100:
                    continue
                
                # Check for data attributes first
                if element.has_attr('data-price'):
                    price = str(element['data-price'])
                    if self.is_valid_price(price):
                        logger.info(f"Debug: Found Metro price in data-price: {price}")
                        return self.format_price(price)
                
                if element.has_attr('data-amount'):
                    price = str(element['data-amount'])
                    if self.is_valid_price(price):
                        logger.info(f"Debug: Found Metro price in data-amount: {price}")
                        return self.format_price(price)
                
                logger.info(f"Debug: Metro selector '{selector}' found text: '{text}'")
                price = self.extract_price_from_text(text)
                if price and self.is_valid_price(price):
                    logger.info(f"Debug: Found Metro price in selector '{selector}': {price}")
                    return price
        
        # If no price found in specific selectors, try broader search
        logger.info("Debug: No price found in specific selectors, trying broader search")
        
        # Focus on main content area
        main_content_selectors = [
            'main', '.main-content', '.content', '.product-content',
            '.product-details', '.product-info', '.product-summary'
        ]
        
        for main_selector in main_content_selectors:
            main_content = soup.select_one(main_selector)
            if main_content:
                text = main_content.get_text()
                price = self.extract_price_from_text(text)
                if price and self.is_valid_price(price):
                    logger.info(f"Debug: Found Metro price in main content: {price}")
                    return self.format_price(price)
        
        # Final fallback: search entire page
        text = soup.get_text()
        price = self.extract_price_from_text(text)
        if price and self.is_valid_price(price):
            logger.info(f"Debug: Found Metro price in entire page: {price}")
            return self.format_price(price)
        
        return None

    def extract_price_from_text(self, text: str) -> Optional[str]:
        """
        Extract price from text using regex patterns
        """
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Price patterns to try
        patterns = [
            r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'Price:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*Rs',
            r'([\d,]+(?:\.\d{2})?)\s*PKR',
            r'Rs\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)',
            r'Price\s*:?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'PKR\s*([\d,]+(?:\.\d{2})?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                price = match.replace(',', '')
                if self.is_valid_price(price):
                    return price
        
        return None

    def is_valid_price(self, price_str: str) -> bool:
        """
        Validate if a string represents a valid price
        """
        try:
            # Remove commas and convert to float
            price = float(price_str.replace(',', ''))
            # Check if price is reasonable (between 1 and 100000)
            return 1 <= price <= 100000
        except (ValueError, TypeError):
            return False

    def format_price(self, price_str: str) -> str:
        """
        Format price string consistently
        """
        try:
            price = float(price_str.replace(',', ''))
            return f"{price:.2f}"
        except (ValueError, TypeError):
            return price_str

    def scrape_price(self, url: str) -> Optional[str]:
        """
        Scrape price from Metro URL using Selenium
        """
        try:
            logger.info(f"Scraping price from Metro: {url}")
            
            # Use Selenium for Metro (special handling)
            return self.get_metro_price_selenium(url)
                
        except Exception as e:
            logger.error(f"Error scraping Metro: {e}")
            return None

    def get_metro_price_selenium(self, url):
        """
        Get Metro price using Selenium (special handling for Metro)
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 20)
            # Try the specific product detail price selector first
            try:
                price_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'p.CategoryGrid_product_details_price__dNQQQ')))
                price_text = price_elem.text.strip()
                price = self.extract_price_from_text(price_text)
                if price and self.is_valid_price(price):
                    return self.format_price(price)
            except Exception:
                # Fallback: try all p.CategoryGrid_product_price__Svf8T elements and pick the lowest
                price_elements = driver.find_elements(By.CSS_SELECTOR, 'p.CategoryGrid_product_price__Svf8T')
                prices = []
                for elem in price_elements:
                    text = elem.text.strip()
                    price = self.extract_price_from_text(text)
                    if price and self.is_valid_price(price):
                        prices.append(float(price))
                if prices:
                    min_price = min(prices)
                    return f"{min_price:.2f}"
            return None
        except Exception as e:
            logger.error(f"Selenium Metro error: {e}")
            return None
        finally:
            driver.quit()

    def process_csv(self, csv_file_path: str):
        """
        Process CSV file and extract Metro data
        """
        logger.info("Starting to process CSV file for Metro...")
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
                
                if len(rows) < 3:
                    logger.error("CSV file doesn't have enough rows")
                    return
                
                # Initialize results structure
                self.results = []
                
                # Process each product row
                for row_idx, row in enumerate(rows[2:], start=3):
                    if len(row) < 6:
                        continue
                    sku = row[0]
                    my_price = row[1]
                    metro_link = row[5]  # Metro link is in column 5 (index 5)
                    
                    if not sku or sku.strip() == '':
                        continue
                    
                    product_data = {
                        'SKU': sku,
                        'my_price': my_price,
                        'Metro_price': '',
                        'Metro_link': metro_link
                    }
                    
                    # Scrape Metro price if link exists
                    if metro_link and metro_link.strip() != '':
                        if row_idx > 3:
                            time.sleep(5)
                        logger.info(f"Processing SKU: {sku} for Metro")
                        price = self.scrape_price(metro_link.strip())
                        if price:
                            product_data['Metro_price'] = price
                            logger.info(f"✅ Metro - {sku}: {price}")
                        else:
                            product_data['Metro_price'] = "None"
                            logger.warning(f"❌ Metro - {sku}: No price found (set to None)")
                    else:
                        product_data['Metro_price'] = "None"
                        logger.info(f"⏭️ Metro - {sku}: No link provided (set to None)")
                    
                    self.results.append(product_data)
                
                logger.info(f"✅ Completed processing Metro data!")
                logger.info(f"Total products processed: {len(self.results)}")
                
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            traceback.print_exc()

    def ensure_metro_columns(self):
        """
        Ensure that Metro columns exist in the table, and add them if not present.
        """
        try:
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                port=3306,
                database="competitor_price_data"
            )
            cursor = conn.cursor()
            # Get current columns
            cursor.execute("SHOW COLUMNS FROM unified_competitor_prices")
            columns = [row[0] for row in cursor.fetchall()]
            # Add Metro columns if missing
            if 'Metro_price' not in columns:
                cursor.execute("ALTER TABLE unified_competitor_prices ADD COLUMN Metro_price VARCHAR(50) AFTER my_price")
            if 'Metro_link' not in columns:
                # Place Metro_link after Metro_price
                cursor.execute("ALTER TABLE unified_competitor_prices ADD COLUMN Metro_link TEXT AFTER Metro_price")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring Metro columns: {e}")
            traceback.print_exc()

    def create_mysql_table(self):
        """
        Create MySQL table with only SKU, my_price if not exists
        """
        try:
            logger.info("Creating MySQL table...")
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                port=3306
            )
            cursor = conn.cursor()
            # Create database if not exists
            cursor.execute("CREATE DATABASE IF NOT EXISTS competitor_price_data")
            cursor.execute("USE competitor_price_data")
            # Create table with only SKU and my_price if not exists
            create_table_query = """
                CREATE TABLE IF NOT EXISTS unified_competitor_prices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    SKU VARCHAR(255),
                    my_price VARCHAR(50)
                )
            """
            cursor.execute(create_table_query)
            logger.info("✅ MySQL table created successfully!")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error creating MySQL table: {e}")
            traceback.print_exc()

    def save_to_mysql(self):
        """
        Save Metro results to MySQL (insert new rows or update only Metro columns)
        """
        try:
            logger.info("Saving Metro data to MySQL...")
            # Ensure columns exist
            self.ensure_metro_columns()
            # Connect to MySQL
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                port=3306,
                database="competitor_price_data"
            )
            cursor = conn.cursor()
            # Insert or update data for each product
            for product in self.results:
                # Check if product already exists
                check_query = "SELECT id FROM unified_competitor_prices WHERE SKU = %s"
                cursor.execute(check_query, (product['SKU'],))
                existing = cursor.fetchone()
                if existing:
                    # Update only Metro columns for existing row
                    update_query = """
                        UPDATE unified_competitor_prices 
                        SET Metro_price = %s, Metro_link = %s, my_price = %s
                        WHERE SKU = %s
                    """
                    cursor.execute(update_query, (
                        product['Metro_price'],
                        product['Metro_link'],
                        product['my_price'],
                        product['SKU']
                    ))
                    logger.info(f"Updated Metro data for SKU: {product['SKU']}")
                else:
                    # Insert new row with only Metro columns
                    insert_query = """
                        INSERT INTO unified_competitor_prices 
                        (SKU, my_price, Metro_price, Metro_link)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (
                        product['SKU'],
                        product['my_price'],
                        product['Metro_price'],
                        product['Metro_link']
                    ))
                    logger.info(f"Inserted new row for SKU: {product['SKU']}")
            conn.commit()
            logger.info(f"✅ Saved {len(self.results)} Metro products to MySQL!")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving to MySQL: {e}")
            traceback.print_exc()

    def save_to_csv(self, output_file: str = 'metro.csv'):
        """
        Save Metro results to CSV file
        """
        try:
            logger.info(f"Saving Metro data to CSV: {output_file}")
            # Prepare CSV headers
            headers = ["SKU", "my_price", "Metro_price", "Metro_link"]
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.results)
            logger.info(f"✅ Saved {len(self.results)} Metro products to CSV!")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            traceback.print_exc()

def main():
    """
    Main function to run the Metro price scraping process
    """
    print("Metro Competitor Price Scraper")
    print("="*50)
    print("📋 Processing: Metro competitor only")
    print("📊 Output: metro.csv")
    print("🗄️  Database: Shared MySQL table")
    print("="*50)
    
    # Initialize scraper
    scraper = MetroPriceScraper()
    
    # Process the CSV file
    csv_file = "Cartpk competitors link(Developer Sample File).csv"
    scraper.process_csv(csv_file)
    
    # Only proceed if we have results
    if scraper.results:
        print("\n" + "="*50)
        print("📊 SAVING DATA")
        print("="*50)
        
        # Create MySQL table (if not exists)
        scraper.create_mysql_table()
        
        # Save to MySQL
        scraper.save_to_mysql()
        
        # Save to CSV
        scraper.save_to_csv()
        
        print("\n🎉 Metro scraping completed successfully!")
        print(f"📊 Total products processed: {len(scraper.results)}")
        print("📁 Data saved to:")
        print("   - MySQL table: unified_competitor_prices")
        print("   - CSV file: metro.csv")
    else:
        print("\n❌ No Metro data to save!")

if __name__ == "__main__":
    main() 