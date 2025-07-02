# Competitor Price Scraper

This Python script fetches product prices from competitor websites based on a CSV file containing product SKUs and competitor links.

## Features

- Processes one competitor at a time to avoid overwhelming servers
- Creates separate CSV files for each competitor
- Handles missing competitor links gracefully
- Extracts prices using multiple pattern matching strategies
- Includes detailed logging and error handling
- Provides progress updates for each competitor

## Output Format

The script generates separate CSV files for each competitor with the naming pattern: `{competitor_name}_prices.csv`

Each CSV file contains the following columns:
- **SKU**: Product identifier
- **Competitor_Price**: Extracted price from the competitor website
- **Competitor_Name**: Name of the competitor (Cartpk, Diamond, Naheed, Metro)
- **Competitor_Link**: URL of the product page

## Generated Files

Based on your CSV file, the script will create:
- `cartpk_prices.csv` - All Cartpk products and prices
- `diamond_prices.csv` - All Diamond products and prices  
- `naheed_prices.csv` - All Naheed products and prices
- `metro_prices.csv` - All Metro products and prices

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Ensure your CSV file is in the same directory as the script
2. Run the script:
```bash
python main.py
```

The script will:
1. Read the CSV file: `Cartpk competitors link(Developer Sample File).csv`
2. Process each competitor sequentially:
   - Complete all SKUs for the first competitor
   - Generate a CSV file for that competitor
   - Move to the next competitor
   - Repeat until all competitors are processed
3. Display progress updates for each competitor

## Processing Order

The script processes competitors in the order they appear in your CSV file:
1. **Cartpk** - First competitor
2. **Diamond** - Second competitor  
3. **Naheed** - Third competitor
4. **Metro** - Fourth competitor

## CSV File Format

The input CSV should have the following structure:
- Row 1: Competitor website URLs
- Row 2: Column headers
- Row 3+: Product data with SKU and competitor links

Example:
```csv
,www.cartpk.com,https://www.dsmonline.pk/clifton,https://www.naheed.pk,https://www.metro-online.pk/home
Cartpk SKU,Cartpk Products Link,Diamond Link,Naheed Link ,Metro Link
Product Name,https://cartpk.com/product,https://dsmonline.pk/product,https://naheed.pk/product,https://metro-online.pk/product
```

## Error Handling

- Missing competitor links are skipped automatically
- Network errors are logged but don't stop the process
- Invalid URLs are handled gracefully
- Price extraction failures are logged for debugging
- Each competitor is processed independently

## Notes

- The script includes delays between requests to be respectful to competitor servers
- 5-second delay between processing different competitors
- 2-second delay between requests to the same competitor
- Price extraction uses multiple strategies to handle different website structures
- All activities are logged for monitoring and debugging
- The script is designed to handle Pakistani e-commerce websites (Cartpk, Diamond, Naheed, Metro) 