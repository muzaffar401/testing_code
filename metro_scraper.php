<?php
require 'vendor/autoload.php';

use Symfony\Component\BrowserKit\HttpBrowser;
use Symfony\Component\HttpClient\HttpClient;
use Symfony\Component\DomCrawler\Crawler;
use Facebook\WebDriver\Remote\RemoteWebDriver;
use Facebook\WebDriver\Remote\DesiredCapabilities;
use Facebook\WebDriver\WebDriverBy;
use Facebook\WebDriver\WebDriverExpectedCondition;
use Facebook\WebDriver\Exception\NoSuchElementException;
use Facebook\WebDriver\Exception\TimeoutException;

class MetroPriceScraper {
    private $session;
    private $competitorName;
    public $results;
    private $logger;

    public function __construct() {
        $this->competitorName = 'Metro';
        $this->results = [];
        
        // Initialize logger (simple file logger)
        $this->logger = fopen('metro_scraper.log', 'a');
        $this->log("Initializing MetroPriceScraper");
        
        // Initialize HTTP client
        $this->session = new HttpBrowser(HttpClient::create([
            'headers' => [
                'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept' => 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language' => 'en-US,en;q=0.5',
                'Accept-Encoding' => 'gzip, deflate',
                'Connection' => 'keep-alive',
                'Upgrade-Insecure-Requests' => '1',
            ],
            'timeout' => 30,
        ]));
    }
    
    private function log($message) {
        $timestamp = date('Y-m-d H:i:s');
        fwrite($this->logger, "[$timestamp] $message\n");
        echo "$message\n";
    }
    
    public function __destruct() {
        fclose($this->logger);
    }
    
    private function extractPriceFromHtml($htmlContent) {
        $crawler = new Crawler($htmlContent);

        // Remove script and style elements
        $crawler->filter('script, style')->each(function (Crawler $crawler) {
            $node = $crawler->getNode(0);
            if ($node) {
                $node->parentNode->removeChild($node);
            }
        });

        // First, try to extract price from JSON data in script tags (Metro stores prices here)
        $scripts = $crawler->filter('script')->each(function (Crawler $node) {
            return $node->text();
        });
        foreach ($scripts as $scriptText) {
            if (strpos($scriptText, '"price"') !== false && strpos($scriptText, '"sell_price"') !== false) {
                $this->log("Debug: Found Metro JSON data with prices");
                // Extract price from JSON
                if (preg_match('/"sell_price":(\d+(?:\.\d+)?)/', $scriptText, $sellPriceMatches)) {
                    $price = $sellPriceMatches[1];
                    $this->log("Debug: Found Metro sell_price: $price");
                    if ($this->isValidPrice($price)) {
                        return $this->formatPrice($price);
                    }
                }
                if (preg_match('/"price":(\d+(?:\.\d+)?)/', $scriptText, $priceMatches)) {
                    $price = $priceMatches[1];
                    $this->log("Debug: Found Metro price: $price");
                    if ($this->isValidPrice($price)) {
                        return $this->formatPrice($price);
                    }
                }
            }
        }

        // Use the specific Metro price selector path
        $priceSelector = "#__next > div > div.main-container > div > div.CategoryGrid_product_details_container_without_imageCarousel__xOYB6 > div.CategoryGrid_product_details_description_container__OjSn3 > p.CategoryGrid_product_details_price__dNQQQ";
        $priceTag = $crawler->filter($priceSelector);
        if ($priceTag->count() > 0) {
            $priceText = $priceTag->text();
            $this->log("Debug: Found Metro price using specific selector: '$priceText'");
            $price = $this->extractPriceFromText($priceText);
            if ($price && $this->isValidPrice($price)) {
                $this->log("Debug: Found Metro price: $price");
                return $this->formatPrice($price);
            }
        }

        // Also try the shorter class name as fallback
        $priceTag = $crawler->filter('p.CategoryGrid_product_details_price__dNQQQ');
        if ($priceTag->count() > 0) {
            $priceText = $priceTag->text();
            $this->log("Debug: Found Metro price using class selector: '$priceText'");
            $price = $this->extractPriceFromText($priceText);
            if ($price && $this->isValidPrice($price)) {
                $this->log("Debug: Found Metro price: $price");
                return $this->formatPrice($price);
            }
        }

        // Fallback to other Metro selectors
        $metroPriceSelectors = [
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
        ];
        foreach ($metroPriceSelectors as $selector) {
            $elements = $crawler->filter($selector);
            foreach ($elements as $element) {
                $elementCrawler = new Crawler($element);
                $text = $elementCrawler->text();
                // Skip very short or very long text
                if (strlen($text) < 3 || strlen($text) > 100) {
                    continue;
                }
                // Check for data attributes first
                if ($element->hasAttribute('data-price')) {
                    $price = $element->getAttribute('data-price');
                    if ($this->isValidPrice($price)) {
                        $this->log("Debug: Found Metro price in data-price: $price");
                        return $this->formatPrice($price);
                    }
                }
                if ($element->hasAttribute('data-amount')) {
                    $price = $element->getAttribute('data-amount');
                    if ($this->isValidPrice($price)) {
                        $this->log("Debug: Found Metro price in data-amount: $price");
                        return $this->formatPrice($price);
                    }
                }
                $this->log("Debug: Metro selector '$selector' found text: '$text'");
                $price = $this->extractPriceFromText($text);
                if ($price && $this->isValidPrice($price)) {
                    $this->log("Debug: Found Metro price in selector '$selector': $price");
                    return $this->formatPrice($price);
                }
            }
        }

        // If no price found in specific selectors, try broader search
        $this->log("Debug: No price found in specific selectors, trying broader search");
        // Focus on main content area
        $mainContentSelectors = [
            'main', '.main-content', '.content', '.product-content',
            '.product-details', '.product-info', '.product-summary'
        ];
        foreach ($mainContentSelectors as $mainSelector) {
            $mainContent = $crawler->filter($mainSelector);
            if ($mainContent->count() > 0) {
                $text = $mainContent->text();
                $price = $this->extractPriceFromText($text);
                if ($price && $this->isValidPrice($price)) {
                    $this->log("Debug: Found Metro price in main content: $price");
                    return $this->formatPrice($price);
                }
            }
        }
        // Final fallback: search entire page
        $text = $crawler->text();
        $price = $this->extractPriceFromText($text);
        if ($price && $this->isValidPrice($price)) {
            $this->log("Debug: Found Metro price in entire page: $price");
            return $this->formatPrice($price);
        }
        return null;
    }
    
    private function extractPriceFromText($text) {
        // Remove extra whitespace and normalize
        $text = preg_replace('/\s+/', ' ', trim($text));
        
        // Price patterns to try
        $patterns = [
            '/Rs\.?\s*([\d,]+(?:\.\d{2})?)/i',
            '/PKR\s*([\d,]+(?:\.\d{2})?)/i',
            '/Price:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)/i',
            '/([\d,]+(?:\.\d{2})?)\s*Rs/i',
            '/([\d,]+(?:\.\d{2})?)\s*PKR/i',
            '/Rs\s*([\d,]+(?:\.\d{2})?)/i',
            '/PKR\s*([\d,]+(?:\.\d{2})?)/i',
            '/([\d,]+(?:\.\d{2})?)/',
            '/Price\s*:?\s*([\d,]+(?:\.\d{2})?)/i',
            '/[\d,]+(?:\.\d{2})?\s*PKR/i',
            '/PKR\s*([\d,]+(?:\.\d{2})?)/i'
        ];
        
        foreach ($patterns as $pattern) {
            if (preg_match_all($pattern, $text, $matches)) {
                foreach ($matches[1] as $match) {
                    $price = str_replace(',', '', $match);
                    if ($this->isValidPrice($price)) {
                        return $price;
                    }
                }
            }
        }
        
        return null;
    }
    
    private function isValidPrice($priceStr) {
        try {
            // Remove commas and convert to float
            $price = floatval(str_replace(',', '', $priceStr));
            // Check if price is reasonable (between 1 and 100000)
            return $price >= 1 && $price <= 100000;
        } catch (Exception $e) {
            return false;
        }
    }
    
    private function formatPrice($priceStr) {
        try {
            $price = floatval(str_replace(',', '', $priceStr));
            return number_format($price, 2, '.', '');
        } catch (Exception $e) {
            return $priceStr;
        }
    }
    
    public function scrapePrice($url) {
        try {
            $this->log("Scraping price from Metro: $url");
            // Use Selenium for Metro (special handling)
            return $this->getMetroPriceSelenium($url);
        } catch (Exception $e) {
            $this->log("Error scraping Metro: " . $e->getMessage());
            return null;
        }
    }
    
    private function getMetroPriceSelenium($url) {
        $host = 'http://localhost:4444/wd/hub'; // Default Selenium server address
        $driver = null;
        try {
            $this->log("Connecting to Selenium WebDriver at $host");
            $capabilities = DesiredCapabilities::chrome();
            $driver = RemoteWebDriver::create($host, $capabilities);
            $driver->get($url);
            sleep(5); // Wait longer for the page to load
            $title = $driver->getTitle();
            if (is_array($title)) {
                $this->log('Page title (array): ' . print_r($title, true));
            } else {
                $this->log('Page title: ' . $title);
            }

            // Try the specific product detail price selector first
            try {
                $priceElem = $driver->wait(20)->until(
                    WebDriverExpectedCondition::presenceOfElementLocated(
                        WebDriverBy::cssSelector('p.CategoryGrid_product_details_price__dNQQQ')
                    )
                );
                $priceText = $priceElem->getText();
                if (is_array($priceText)) {
                    $priceText = implode(' ', $priceText);
                }
                $price = $this->extractPriceFromText($priceText);
                if ($price && $this->isValidPrice($price)) {
                    return $this->formatPrice($price);
                }
            } catch (NoSuchElementException | TimeoutException $e) {
                // Fallback: try all p.CategoryGrid_product_price__Svf8T elements and pick the lowest
                $priceElements = $driver->findElements(WebDriverBy::cssSelector('p.CategoryGrid_product_price__Svf8T'));
                $prices = [];
                foreach ($priceElements as $elem) {
                    $text = $elem->getText();
                    if (is_array($text)) {
                        $text = implode(' ', $text);
                    }
                    $price = $this->extractPriceFromText($text);
                    if ($price && $this->isValidPrice($price)) {
                        $prices[] = floatval($price);
                    }
                }
                if (!empty($prices)) {
                    $minPrice = min($prices);
                    return number_format($minPrice, 2, '.', '');
                }
            }
            return null;
        } catch (Exception $e) {
            $this->log("Selenium/WebDriver error: " . $e->getMessage() . ". Make sure Selenium server (e.g. ChromeDriver) is running at $host");
            return null;
        } finally {
            if ($driver) {
                $driver->quit();
            }
        }
    }
    
    public function processCsv($csvFilePath) {
        $this->log("Starting to process CSV file for Metro...");
        
        try {
            if (!file_exists($csvFilePath)) {
                throw new Exception("CSV file not found: $csvFilePath");
            }
            
            $file = fopen($csvFilePath, 'r');
            if (!$file) {
                throw new Exception("Could not open CSV file: $csvFilePath");
            }
            
            // Initialize results structure
            $this->results = [];
            
            // Skip header rows (first 2 rows)
            fgetcsv($file); // First row - competitor names
            fgetcsv($file); // Second row - column headers
            
            $rowIdx = 3; // Starting from row 3 (0-based index would be 2)
            
            // Process each product row
            while (($row = fgetcsv($file)) !== false) {
                if (count($row) < 5) {
                    continue;
                }
                
                $sku = $row[0];
                $myPrice = $row[1];
                $metroLink = $row[4]; // Metro link is in column 4 (index 4)
                
                if (empty($sku)) {
                    continue;
                }
                
                $productData = [
                    'SKU' => $sku,
                    'my_price' => $myPrice,
                    'Metro_price' => '',
                    'Metro_link' => $metroLink
                ];
                
                // Scrape Metro price if link exists
                if (!empty($metroLink)) {
                    if ($rowIdx > 3) {
                        sleep(5); // Add delay between requests
                    }
                    
                    $this->log("Processing SKU: $sku for Metro");
                    $price = $this->scrapePrice(trim($metroLink));
                    
                    if ($price) {
                        $productData['Metro_price'] = $price;
                        $this->log("✅ Metro - $sku: $price");
                    } else {
                        $productData['Metro_price'] = "None";
                        $this->log("❌ Metro - $sku: No price found (set to None)");
                    }
                } else {
                    $productData['Metro_price'] = "None";
                    $this->log("⏭️ Metro - $sku: No link provided (set to None)");
                }
                
                $this->results[] = $productData;
                $rowIdx++;
            }
            
            fclose($file);
            
            $this->log("✅ Completed processing Metro data!");
            $this->log("Total products processed: " . count($this->results));
            
            // Save results to CSV
            echo "Processing complete. Results count: " . count($this->results) . "\n";
            if (!empty($this->results)) {
                $this->saveToCsv();
            } else {
                echo "❌ No Metro data to save!\n";
            }
            
        } catch (Exception $e) {
            $this->log("Error processing CSV file: " . $e->getMessage());
        }
    }
    
    public function createMysqlTable() {
        try {
            $this->log("Creating MySQL table...");
            
            // Connect to MySQL
            $conn = new mysqli("localhost", "root", "", "", 3306);
            
            if ($conn->connect_error) {
                throw new Exception("Connection failed: " . $conn->connect_error);
            }
            
            // Create database if not exists
            $conn->query("CREATE DATABASE IF NOT EXISTS competitor_price_data");
            $conn->select_db("competitor_price_data");
            
            // Create table with only Metro columns
            $createTableQuery = "
                CREATE TABLE IF NOT EXISTS unified_competitor_prices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    SKU VARCHAR(255),
                    my_price VARCHAR(50),
                    Metro_price VARCHAR(50),
                    Metro_link TEXT
                )
            ";
            
            if (!$conn->query($createTableQuery)) {
                throw new Exception("Error creating table: " . $conn->error);
            }
            
            $this->log("✅ MySQL table created successfully!");
            $conn->close();
            
        } catch (Exception $e) {
            $this->log("Error creating MySQL table: " . $e->getMessage());
        }
    }
    
    public function saveToMysql() {
        try {
            $this->log("Saving Metro data to MySQL...");
            
            // Connect to MySQL
            $conn = new mysqli("localhost", "root", "", "competitor_price_data", 3306);
            
            if ($conn->connect_error) {
                throw new Exception("Connection failed: " . $conn->connect_error);
            }
            
            // Insert data for each product
            foreach ($this->results as $product) {
                // Check if product already exists
                $checkQuery = "SELECT id FROM unified_competitor_prices WHERE SKU = ?";
                $stmt = $conn->prepare($checkQuery);
                $stmt->bind_param("s", $product['SKU']);
                $stmt->execute();
                $result = $stmt->get_result();
                $existing = $result->fetch_assoc();
                $stmt->close();
                
                if ($existing) {
                    // Update existing row with Metro data
                    $updateQuery = "
                        UPDATE unified_competitor_prices 
                        SET my_price = ?, Metro_price = ?, Metro_link = ?
                        WHERE SKU = ?
                    ";
                    $stmt = $conn->prepare($updateQuery);
                    $stmt->bind_param("ssss", 
                        $product['my_price'],
                        $product['Metro_price'],
                        $product['Metro_link'],
                        $product['SKU']
                    );
                    $stmt->execute();
                    $stmt->close();
                    $this->log("Updated Metro data for SKU: " . $product['SKU']);
                } else {
                    // Insert new row with Metro data
                    $insertQuery = "
                        INSERT INTO unified_competitor_prices 
                        (SKU, my_price, Metro_price, Metro_link)
                        VALUES (?, ?, ?, ?)
                    ";
                    $stmt = $conn->prepare($insertQuery);
                    $stmt->bind_param("ssss", 
                        $product['SKU'],
                        $product['my_price'],
                        $product['Metro_price'],
                        $product['Metro_link']
                    );
                    $stmt->execute();
                    $stmt->close();
                    $this->log("Inserted new row for SKU: " . $product['SKU']);
                }
            }
            
            $this->log("✅ Saved " . count($this->results) . " Metro products to MySQL!");
            $conn->close();
            
        } catch (Exception $e) {
            $this->log("Error saving to MySQL: " . $e->getMessage());
        }
    }
    
    public function saveToCsv($outputFile = 'metro.csv') {
        try {
            $this->log("Saving Metro data to CSV: $outputFile");
            
            // Prepare CSV headers
            $headers = ["SKU", "my_price", "Metro_price", "Metro_link"];
            
            // Write to CSV
            $file = fopen($outputFile, 'w');
            if (!$file) {
                throw new Exception("Could not open file for writing: $outputFile");
            }
            
            // Write headers
            fputcsv($file, $headers);
            
            // Write data rows
            foreach ($this->results as $row) {
                fputcsv($file, $row);
            }
            
            fclose($file);
            $this->log("✅ Saved " . count($this->results) . " Metro products to CSV!");
            
        } catch (Exception $e) {
            $this->log("Error saving to CSV: " . $e->getMessage());
        }
    }
}

function main() {
    echo "Metro Competitor Price Scraper\n";
    echo str_repeat("=", 50) . "\n";
    echo "📋 Processing: Metro competitor only\n";
    echo "📊 Output: metro.csv\n";
    echo "🗄️  Database: Shared MySQL table\n";
    echo str_repeat("=", 50) . "\n";
    
    // Initialize scraper
    $scraper = new MetroPriceScraper();
    
    // Process the CSV file
    $csvFile = "Cartpk competitors link(Developer Sample File).csv";
    $scraper->processCsv($csvFile);
    
    // Only proceed if we have results
    echo "\nResults count: " . count($scraper->results) . "\n";
    if (!empty($scraper->results)) {
        echo "\n" . str_repeat("=", 50) . "\n";
        echo "📊 SAVING DATA\n";
        echo str_repeat("=", 50) . "\n";
        
        // Create MySQL table (if not exists)
        $scraper->createMysqlTable();
        
        // Save to MySQL
        $scraper->saveToMysql();
        
        // Save to CSV
        $scraper->saveToCsv();
        
        echo "\n🎉 Metro scraping completed successfully!\n";
        echo "📊 Total products processed: " . count($scraper->results) . "\n";
        echo "📁 Data saved to:\n";
        echo "   - MySQL table: unified_competitor_prices\n";
        echo "   - CSV file: metro.csv\n";
    } else {
        echo "\n❌ No Metro data to save!\n";
    }
}

// Run the main function
main();