import csv
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import logging
from typing import List, Dict, Optional, Tuple
import pymysql
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiamondPriceScraper:
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
        self.competitor_name = 'Diamond'
        self.results = []
        
    def extract_price_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract price from HTML content for Diamond
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Diamond-specific selectors
        diamond_selectors = [
            '.price', '.product-price', '.amount', '[class*="price"]',
            '[class*="Price"]', '.current-price', '.regular-price',
            '.product-details-price', '.price-box', '.price-wrapper'
        ]
        
        # Try Diamond-specific selectors first
        for selector in diamond_selectors:
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

    def scrape_price(self, url: str) -> Optional[str]:
        """
        Scrape price from Diamond URL
        """
        try:
            logger.info(f"Scraping price from Diamond: {url}")
            
            response = self.session.get(url, timeout=30)
            
            # Check for HTTP errors (404, 500, etc.)
            if response.status_code >= 400:
                logger.error(f"HTTP {response.status_code} error for Diamond: {url}")
                return None
            
            # Extract price from HTML
            price = self.extract_price_from_html(response.text)
            
            if price:
                logger.info(f"Found price for Diamond: {price}")
                return price
            else:
                logger.warning(f"No price found for Diamond: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for Diamond: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping Diamond: {e}")
            return None

    def process_csv(self, csv_file_path: str):
        """
        Process CSV file and extract Diamond data
        """
        logger.info("Starting to process CSV file for Diamond...")
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
                    diamond_link = row[3]  # Diamond link is in column 3 (index 3)
                    
                    if not sku or sku.strip() == '':
                        continue
                    
                    product_data = {
                        'SKU': sku,
                        'my_price': my_price,
                        'Diamond_price': '',
                        'Diamond_link': diamond_link
                    }
                    
                    # Scrape Diamond price if link exists
                    if diamond_link and diamond_link.strip() != '':
                        if row_idx > 3:
                            time.sleep(5)
                        logger.info(f"Processing SKU: {sku} for Diamond")
                        price = self.scrape_price(diamond_link.strip())
                        if price:
                            product_data['Diamond_price'] = price
                            logger.info(f"✅ Diamond - {sku}: {price}")
                        else:
                            product_data['Diamond_price'] = "None"
                            logger.warning(f"❌ Diamond - {sku}: No price found (set to None)")
                    else:
                        product_data['Diamond_price'] = "None"
                        logger.info(f"⏭️ Diamond - {sku}: No link provided (set to None)")
                    
                    self.results.append(product_data)
                
                logger.info(f"✅ Completed processing Diamond data!")
                logger.info(f"Total products processed: {len(self.results)}")
                
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            traceback.print_exc()

    def ensure_diamond_columns(self):
        """
        Ensure that Diamond columns exist in the table, and add them if not present.
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
            # Add Diamond columns if missing
            if 'Diamond_price' not in columns:
                cursor.execute("ALTER TABLE unified_competitor_prices ADD COLUMN Diamond_price VARCHAR(50) AFTER my_price")
            if 'Diamond_link' not in columns:
                # Place Diamond_link after Diamond_price
                cursor.execute("ALTER TABLE unified_competitor_prices ADD COLUMN Diamond_link TEXT AFTER Diamond_price")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring Diamond columns: {e}")
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
        Save Diamond results to MySQL (insert new rows or update only Diamond columns)
        """
        try:
            logger.info("Saving Diamond data to MySQL...")
            # Ensure columns exist
            self.ensure_diamond_columns()
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
                    # Update only Diamond columns for existing row
                    update_query = """
                        UPDATE unified_competitor_prices 
                        SET Diamond_price = %s, Diamond_link = %s, my_price = %s
                        WHERE SKU = %s
                    """
                    cursor.execute(update_query, (
                        product['Diamond_price'],
                        product['Diamond_link'],
                        product['my_price'],
                        product['SKU']
                    ))
                    logger.info(f"Updated Diamond data for SKU: {product['SKU']}")
                else:
                    # Insert new row with only Diamond columns
                    insert_query = """
                        INSERT INTO unified_competitor_prices 
                        (SKU, my_price, Diamond_price, Diamond_link)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (
                        product['SKU'],
                        product['my_price'],
                        product['Diamond_price'],
                        product['Diamond_link']
                    ))
                    logger.info(f"Inserted new row for SKU: {product['SKU']}")
            conn.commit()
            logger.info(f"✅ Saved {len(self.results)} Diamond products to MySQL!")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving to MySQL: {e}")
            traceback.print_exc()

    def save_to_csv(self, output_file: str = 'diamond.csv'):
        """
        Save Diamond results to CSV file
        """
        try:
            logger.info(f"Saving Diamond data to CSV: {output_file}")
            # Prepare CSV headers
            headers = ["SKU", "my_price", "Diamond_price", "Diamond_link"]
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.results)
            logger.info(f"✅ Saved {len(self.results)} Diamond products to CSV!")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            traceback.print_exc()

def main():
    """
    Main function to run the Diamond price scraping process
    """
    print("Diamond Competitor Price Scraper")
    print("="*50)
    print("📋 Processing: Diamond competitor only")
    print("📊 Output: diamond.csv")
    print("🗄️  Database: Shared MySQL table")
    print("="*50)
    
    # Initialize scraper
    scraper = DiamondPriceScraper()
    
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
        
        print("\n🎉 Diamond scraping completed successfully!")
        print(f"📊 Total products processed: {len(scraper.results)}")
        print("📁 Data saved to:")
        print("   - MySQL table: unified_competitor_prices")
        print("   - CSV file: diamond.csv")
    else:
        print("\n❌ No Diamond data to save!")

if __name__ == "__main__":
    main() 