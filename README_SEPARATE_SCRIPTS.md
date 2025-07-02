# Separate Competitor Price Scrapers

This directory now contains separate Python scripts for each competitor, allowing you to run them independently while maintaining a shared MySQL database.

## Available Scripts

### 1. `diamond_scraper.py`
- **Purpose**: Scrapes prices from Diamond competitor only
- **Output**: `diamond.csv`
- **Database**: Updates/inserts into shared `unified_competitor_prices` table

### 2. `naheed_scraper.py`
- **Purpose**: Scrapes prices from Naheed competitor only
- **Output**: `naheed.csv`
- **Database**: Updates/inserts into shared `unified_competitor_prices` table

### 3. `metro_scraper.py`
- **Purpose**: Scrapes prices from Metro competitor only (uses Selenium)
- **Output**: `metro.csv`
- **Database**: Updates/inserts into shared `unified_competitor_prices` table

## How to Use

### Running Individual Scripts

```bash
# Run Diamond scraper only
python diamond_scraper.py

# Run Naheed scraper only
python naheed_scraper.py

# Run Metro scraper only
python metro_scraper.py
```

### What Each Script Does

1. **Reads the CSV file**: `Cartpk competitors link(Developer Sample File).csv`
2. **Processes only that competitor's data**: Extracts links for the specific competitor
3. **Scrapes prices**: Uses appropriate method (requests for Diamond/Naheed, Selenium for Metro)
4. **Saves to CSV**: Creates a competitor-specific CSV file (e.g., `diamond.csv`)
5. **Updates MySQL**: Inserts/updates data in the shared `unified_competitor_prices` table

### Database Behavior

- **First run**: Creates the `unified_competitor_prices` table if it doesn't exist
- **New products**: Inserts new rows for products not in the database
- **Existing products**: Updates the competitor-specific columns for existing products
- **Shared table**: All competitors' data goes into the same table structure

### CSV Structure

Each script generates a CSV with these columns:
- `SKU`: Product SKU
- `my_price`: Your product price
- `[Competitor]_price`: Scraped price from that competitor
- `[Competitor]_link`: Link to the competitor's product page

### MySQL Table Structure

The shared table has this structure:
```sql
CREATE TABLE unified_competitor_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    SKU VARCHAR(255),
    my_price VARCHAR(50),
    Diamond_price VARCHAR(50),
    Diamond_link TEXT,
    Naheed_price VARCHAR(50),
    Naheed_link TEXT,
    Metro_price VARCHAR(50),
    Metro_link TEXT
)
```

## Benefits

1. **Independent execution**: Run only the competitor you need
2. **Faster processing**: No need to wait for all competitors
3. **Focused debugging**: Easier to troubleshoot issues with specific competitors
4. **Shared database**: All data still goes into one unified table
5. **Individual CSV files**: Get separate reports for each competitor

## Requirements

Make sure you have all the required dependencies installed:
```bash
pip install -r requirements.txt
```

## Notes

- **Metro scraper**: Uses Selenium with Chrome WebDriver for dynamic content
- **Diamond/Naheed scrapers**: Use standard requests for static content
- **Rate limiting**: Each script includes 5-second delays between requests
- **Error handling**: Comprehensive logging and error handling for each competitor
- **Database updates**: Smart update/insert logic to avoid duplicates

## Example Usage

```bash
# Run all competitors in sequence
python diamond_scraper.py
python naheed_scraper.py
python metro_scraper.py

# Or run just one when you need it
python diamond_scraper.py
```

This will give you:
- `diamond.csv` with Diamond data
- `naheed.csv` with Naheed data  
- `metro.csv` with Metro data
- All data in the shared `unified_competitor_prices` MySQL table 