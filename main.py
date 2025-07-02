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

class CompetitorPriceScraper:
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
        self.unified_results = []
        self.competitor_names = []
        
    def extract_price_from_html(self, html_content: str, competitor_name: str) -> Optional[str]:
        """
        Extract price from HTML content based on competitor-specific patterns
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Common price patterns
        price_patterns = [
            r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'Price:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*Rs',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'Rs\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*Rs',
            r'([\d,]+(?:\.\d{2})?)\s*PKR',
            # Metro specific patterns
            r'[\d,]+(?:\.\d{2})?',
            r'Price\s*:?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'PKR\s*([\d,]+(?:\.\d{2})?)'
        ]
        
        # Competitor-specific selectors
        competitor_selectors = {
            'Cartpk': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Diamond': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Naheed': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Metro': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper',
                '.product-price-box', '.price-display', '.price-value',
                '.product-price-value', '.price-amount', '.product-amount',
                '[data-price]', '[data-amount]', '.cost', '.value',
                '.product-cost', '.product-value', '.selling-price',
                '.offer-price', '.discount-price', '.final-price'
            ]
        }
        
        # Special handling for Metro
        if competitor_name == 'Metro':
            logger.info(f"Debug: Analyzing Metro page structure")
            
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
            
            # Use the specific Metro price selector path provided by user
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
            
            # Fallback to other Metro selectors if the specific class is not found
            metro_price_selectors = [
                # Primary Metro selectors - focus on product areas
                '.product-price', '.price-display', '.price-value',
                '.product-price-value', '.price-amount', '.product-amount',
                '.selling-price', '.offer-price', '.discount-price', '.final-price',
                '.price-box', '.price-container', '.product-price-box',
                '.price-wrapper', '.price-section', '.product-price-section',
                # More specific Metro selectors
                '.product-details-price', '.current-price', '.regular-price',
                '.product-price-display', '.price-text', '.price-label',
                # Generic price selectors
                '.price', '.amount', '.product-price',
                '[class*="price"]', '[class*="Price"]', '[class*="amount"]',
                '[class*="Amount"]', '[class*="cost"]', '[class*="Cost"]',
                # Data attributes
                '[data-price]', '[data-amount]', '[data-value]',
                # Additional Metro specific patterns
                '.cost', '.value', '.product-cost', '.product-value',
                # Metro specific product containers
                '.product-details', '.product-info', '.product-summary',
                '.product-description', '.product-content'
            ]
            
            # First try to find price in specific Metro elements
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
            
            # If no price found in specific selectors, try broader search with better filtering
            logger.info("Debug: No price found in specific selectors, trying broader search")
            
            # Focus on main content area, avoid header/footer
            main_content_selectors = [
                'main', '.main-content', '.content', '.product-content',
                '.product-details', '.product-info', '.product-summary'
            ]
            
            for main_selector in main_content_selectors:
                main_content = soup.select_one(main_selector)
                if main_content:
                    # Search for price patterns in main content
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
        
        # For other competitors, use their specific selectors
        if competitor_name in competitor_selectors:
            for selector in competitor_selectors[competitor_name]:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    price = self.extract_price_from_text(text)
                    if price and self.is_valid_price(price):
                        return self.format_price(price)
        
        # Fallback: search entire text for price patterns
        text = soup.get_text()
        return self.extract_price_from_text(text)

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

    def scrape_price(self, url: str, competitor_name: str) -> Optional[str]:
        """
        Scrape price from a given URL for a specific competitor
        """
        try:
            logger.info(f"Scraping price from {competitor_name}: {url}")
            
            # Special handling for Metro using Selenium
            if competitor_name == 'Metro':
                return self.get_metro_price_selenium(url)
            
            # For other competitors, use requests
            response = self.session.get(url, timeout=30)
            
            # Check for HTTP errors (404, 500, etc.)
            if response.status_code >= 400:
                logger.error(f"HTTP {response.status_code} error for {competitor_name}: {url}")
                return None
            
            # Extract price from HTML
            price = self.extract_price_from_html(response.text, competitor_name)
            
            if price:
                logger.info(f"Found price for {competitor_name}: {price}")
                return price
            else:
                logger.warning(f"No price found for {competitor_name}: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {competitor_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {competitor_name}: {e}")
            return None

    def get_competitor_name_from_url(self, url: str) -> str:
        """
        Extract competitor name from URL
        """
        if 'cartpk.com' in url:
            return 'Cartpk'
        elif 'dsmonline.pk' in url:
            return 'Diamond'
        elif 'naheed.pk' in url:
            return 'Naheed'
        elif 'metro-online.pk' in url:
            return 'Metro'
        else:
            return 'Unknown'

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
        Process CSV file and create unified results structure
        """
        logger.info("Starting to process CSV file...")
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
                
                if len(rows) < 3:
                    logger.error("CSV file doesn't have enough rows")
                    return
                
                # Set competitor names in order (excluding Cartpk as it's your own product)
                self.competitor_names = ['Diamond', 'Naheed', 'Metro']
                logger.info(f"Found competitors: {self.competitor_names}")
                
                # Initialize unified results structure - create all products first
                self.unified_results = []
                
                # First pass: Create all product entries with SKU, my_price
                logger.info("Creating product structure...")
                for row_idx, row in enumerate(rows[2:], start=3):
                    if len(row) < 6:
                        continue
                    sku = row[0]
                    my_price = row[1]
                    links = row[2:6]  # Cartpk, Diamond, Naheed, Metro
                    if not sku or sku.strip() == '':
                        continue
                    product_data = {
                        'SKU': sku,
                        'my_price': my_price
                    }
                    
                    # Add competitor data (skip Cartpk)
                    for i, comp_name in enumerate(self.competitor_names):
                        product_data[f'{comp_name}_price'] = ''
                        product_data[f'{comp_name}_link'] = links[i+1] if i+1 < len(links) else ''
                    self.unified_results.append(product_data)
                logger.info(f"Created {len(self.unified_results)} product entries")
                
                # Process each competitor completely before moving to next
                for comp_idx, comp_name in enumerate(self.competitor_names):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Processing competitor: {comp_name}")
                    logger.info(f"{'='*60}")
                    for row_idx, row in enumerate(rows[2:], start=3):
                        if len(row) < 6:
                            continue
                        sku = row[0]
                        if not sku or sku.strip() == '':
                            continue
                        # Find the corresponding product in unified_results
                        existing_product = None
                        for product in self.unified_results:
                            if product['SKU'] == sku:
                                existing_product = product
                                break
                        if existing_product is None:
                            logger.warning(f"Product {sku} not found in unified_results")
                            continue
                        
                        # Process competitor links
                        product_link = existing_product[f'{comp_name}_link']
                        if product_link and product_link.strip() != '':
                            if row_idx > 3:
                                time.sleep(5)
                            logger.info(f"Processing SKU: {sku} for {comp_name}")
                            price = self.scrape_price(product_link.strip(), comp_name)
                            if price:
                                existing_product[f'{comp_name}_price'] = price
                                logger.info(f"✅ {comp_name} - {sku}: {price}")
                            else:
                                existing_product[f'{comp_name}_price'] = "None"
                                logger.warning(f"❌ {comp_name} - {sku}: No price found (set to None)")
                        else:
                            existing_product[f'{comp_name}_price'] = "None"
                            logger.info(f"⏭️ {comp_name} - {sku}: No link provided (set to None)")
                    logger.info(f"✅ Completed processing all products for {comp_name}")
                    if comp_idx < len(self.competitor_names) - 1:
                        logger.info("Waiting 10 seconds before processing next competitor...")
                        time.sleep(10)
                logger.info(f"\n🎉 Completed processing all competitors!")
                logger.info(f"Total products processed: {len(self.unified_results)}")
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            traceback.print_exc()

    def create_mysql_table(self):
        """
        Create MySQL table with the unified structure
        """
        try:
            logger.info("Creating MySQL table...")
            
            # Connect to MySQL
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
            
            # Create table with dynamic columns based on competitors
            columns = ["id INT AUTO_INCREMENT PRIMARY KEY", "SKU VARCHAR(255)", "my_price VARCHAR(50)"]
            
            # Add competitor columns
            for comp_name in self.competitor_names:
                columns.append(f"{comp_name}_price VARCHAR(50)")
                columns.append(f"{comp_name}_link TEXT")
            
            create_table_query = f"""
                CREATE TABLE IF NOT EXISTS unified_competitor_prices (
                    {', '.join(columns)}
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
        Save unified results to MySQL
        """
        try:
            logger.info("Saving data to MySQL...")
            
            # Connect to MySQL
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                port=3306,
                database="competitor_price_data"
            )
            
            cursor = conn.cursor()
            
            # Prepare insert query
            columns = ["SKU", "my_price"]
            for comp_name in self.competitor_names:
                columns.append(f"{comp_name}_price")
                columns.append(f"{comp_name}_link")
            
            placeholders = ", ".join(["%s"] * len(columns))
            insert_query = f"""
                INSERT INTO unified_competitor_prices ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            # Insert data
            for product in self.unified_results:
                values = [product["SKU"], product["my_price"]]
                for comp_name in self.competitor_names:
                    values.append(product[f"{comp_name}_price"])
                    values.append(product[f"{comp_name}_link"])
                
                cursor.execute(insert_query, values)
            
            conn.commit()
            logger.info(f"✅ Saved {len(self.unified_results)} products to MySQL!")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving to MySQL: {e}")
            traceback.print_exc()

    def save_to_csv(self, output_file: str = 'unified_competitor_prices.csv'):
        """
        Save unified results to CSV file
        """
        try:
            logger.info(f"Saving data to CSV: {output_file}")
            # Prepare CSV headers
            headers = ["SKU", "my_price"]
            for comp_name in self.competitor_names:
                headers.append(f"{comp_name}_price")
                headers.append(f"{comp_name}_link")
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.unified_results)
            logger.info(f"✅ Saved {len(self.unified_results)} products to CSV!")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            traceback.print_exc()

def main():
    """
    Main function to run the unified price scraping process
    """
    print("Unified Competitor Price Scraper")
    print("="*50)
    print("📋 Processing order: One competitor at a time (all products)")
    print("📊 Output: Single CSV with unified structure")
    print("🗄️  Database: MySQL table with same structure")
    print("="*50)
    
    # Initialize scraper
    scraper = CompetitorPriceScraper()
    
    # Process the CSV file
    csv_file = "Cartpk competitors link(Developer Sample File).csv"
    scraper.process_csv(csv_file)
    
    # Only proceed if we have results
    if scraper.unified_results:
        print("\n" + "="*50)
        print("📊 CREATING DATABASE AND SAVING DATA")
        print("="*50)
        
        # Create MySQL table
        scraper.create_mysql_table()
        
        # Save to MySQL
        scraper.save_to_mysql()
        
        # Save to CSV (only after all processing is complete)
        scraper.save_to_csv()
        
        print("\n🎉 Process completed successfully!")
        print(f"📊 Total products processed: {len(scraper.unified_results)}")
        print("📁 Data saved to:")
        print("   - MySQL table: unified_competitor_prices")
        print("   - CSV file: unified_competitor_prices.csv")
        print("\n📋 CSV Structure:")
        print("   - Column 1: SKU")
        print("   - Column 2: my_price")
        print("   - Column 3+: [Competitor]_price, [Competitor]_link (for each competitor)")
    else:
        print("\n❌ No data to save!")

if __name__ == "__main__":
    main()
