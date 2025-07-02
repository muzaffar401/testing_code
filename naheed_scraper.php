<?php
/**
 * Naheed Price Scraper - Complete and Corrected PHP Version
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

// Set up logging with file output
function logMessage($level, $message) {
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$level] $message\n";
    echo $logEntry;
    file_put_contents('naheed_scraper.log', $logEntry, FILE_APPEND);
}

class NaheedPriceScraper {
    private $session;
    private $competitor_name;
    public $results;
    private $default_headers;
    private $debugMode;
    
    public function __construct($debugMode = false) {
        $this->competitor_name = 'Naheed';
        $this->results = [];
        $this->debugMode = $debugMode;
        
        $this->default_headers = [
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language: en-US,en;q=0.5',
            'Accept-Encoding: gzip, deflate',
            'Connection: keep-alive',
            'Upgrade-Insecure-Requests: 1',
            'Referer: https://www.google.com/',
            'Cache-Control: max-age=0'
        ];
        
        $this->initCurlSession();
    }
    
    private function initCurlSession() {
        $this->session = curl_init();
        curl_setopt_array($this->session, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_CONNECTTIMEOUT => 15,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            CURLOPT_HTTPHEADER => $this->default_headers,
            CURLOPT_ENCODING => 'gzip, deflate',
            CURLOPT_COOKIEFILE => '', // Enable cookie handling
            CURLOPT_SSL_VERIFYPEER => false // For testing only, remove in production
        ]);
    }
    
    public function __destruct() {
        if ($this->session) {
            curl_close($this->session);
        }
    }
    
    public function setDebugMode($enable) {
        $this->debugMode = (bool)$enable;
    }
    
    /**
     * Improved HTML content fetching with retries
     */
    private function fetchHtmlContent($url, $maxRetries = 3) {
        $retryCount = 0;
        
        while ($retryCount < $maxRetries) {
            try {
                curl_setopt($this->session, CURLOPT_URL, $url);
                $response = curl_exec($this->session);
                $httpCode = curl_getinfo($this->session, CURLINFO_HTTP_CODE);
                
                if ($httpCode >= 400) {
                    logMessage('WARNING', "HTTP $httpCode error for URL: $url (Attempt ".($retryCount+1).")");
                    $retryCount++;
                    sleep(2);
                    continue;
                }
                
                if ($response === false) {
                    logMessage('WARNING', "cURL error: " . curl_error($this->session)." (Attempt ".($retryCount+1).")");
                    $retryCount++;
                    sleep(2);
                    continue;
                }
                
                return $response;
                
            } catch (Exception $e) {
                logMessage('WARNING', "Exception during fetch: ".$e->getMessage()." (Attempt ".($retryCount+1).")");
                $retryCount++;
                sleep(2);
            }
        }
        
        logMessage('ERROR', "Failed to fetch content after $maxRetries attempts for URL: $url");
        return null;
    }
    
    /**
     * Enhanced price extraction from HTML
     */
    public function extractPriceFromHtml($htmlContent, $url = '') {
        if (empty($htmlContent)) {
            logMessage('DEBUG', "Empty HTML content for URL: $url");
            return null;
        }
        
        // Create DOMDocument with better error handling
        $dom = new DOMDocument();
        $internalErrors = libxml_use_internal_errors(true);
        
        // Load HTML with options to handle malformed content
        if (!$dom->loadHTML($htmlContent, LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD)) {
            logMessage('DEBUG', "Failed to parse HTML for URL: $url");
            libxml_clear_errors();
            libxml_use_internal_errors($internalErrors);
            return $this->extractPriceFromText($htmlContent);
        }
        
        libxml_clear_errors();
        libxml_use_internal_errors($internalErrors);
        
        $xpath = new DOMXPath($dom);
        
        // Enhanced XPath selectors for Naheed
        $priceSelectors = [
            // Price in meta tags (returns attribute nodes)
            '//meta[@property="product:price:amount"]/@content',
            '//meta[@itemprop="price"]/@content',
            
            // Common price class patterns (returns element nodes)
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' price ')]",
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' product-price ')]",
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' current-price ')]",
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' special-price ')]",
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' amount ')]",
            "//*[contains(@class, 'price') and not(contains(@class, 'old'))]",
            
            // Naheed-specific selectors
            "//span[@class='price']",
            "//span[contains(@class, 'special-price')]",
            "//span[@class='price-final']",
            "//div[contains(@class, 'product-info-price')]//span[@class='price']",
            "//span[@data-price-type='finalPrice']",
            "//div[@class='price-box']//span[@class='price']",
            "//span[@class='amount']",
            
            // Price in data attributes (returns element nodes)
            "//*[@data-price]",
            "//*[@data-product-price]",
            
            // Specific elements that might contain price (returns element nodes)
            "//span[@id='price']",
            "//div[@id='price']",
            "//span[@id='productPrice']",
            "//div[@id='productPrice']",
            
            // Currency-specific selectors (returns element nodes)
            "//*[contains(text(), 'Rs.') or contains(text(), 'PKR')]",
            "//*[contains(., 'Rs.') or contains(., 'PKR')]"
        ];
        
        // Try each selector until we find a price
        foreach ($priceSelectors as $selector) {
            try {
                $elements = $xpath->query($selector);
                if ($elements === false || $elements->length === 0) {
                    continue;
                }
                
                foreach ($elements as $element) {
                    $text = '';
                    
                    // Handle attribute nodes differently from element nodes
                    if ($element instanceof DOMAttr) {
                        $text = trim($element->value);
                    } elseif ($element instanceof DOMElement) {
                        $text = trim($element->nodeValue);
                        // For element nodes, check content attribute if it exists
                        if ($element->hasAttribute('content')) {
                            $text = trim($element->getAttribute('content'));
                        }
                    } else {
                        $text = trim($element->nodeValue);
                    }
                    
                    logMessage('DEBUG', "Testing element with text: $text");
                    $price = $this->extractPriceFromText($text);
                    
                    if ($price && $this->isValidPrice($price)) {
                        logMessage('DEBUG', "Found valid price using selector: $selector");
                        return $this->formatPrice($price);
                    }
                }
            } catch (Exception $e) {
                logMessage('DEBUG', "Error with selector $selector: " . $e->getMessage());
                continue;
            }
        }
        
        // Fallback to text extraction if no selectors worked
        logMessage('DEBUG', "No price found with selectors, falling back to full text extraction");
        return $this->extractPriceFromText($dom->textContent);
    }
    
    /**
     * Enhanced price extraction from text
     */
    public function extractPriceFromText($text) {
        if (empty($text)) {
            return null;
        }
        
        // Normalize text
        $text = preg_replace('/\s+/', ' ', trim($text));
        $text = str_replace(['\r', '\n', '\t'], ' ', $text);
        
        // More comprehensive price patterns
        $patterns = [
            // Standard currency formats
            '/Rs\.?\s*([\d,]+(?:\.\d{2})?)/i',
            '/PKR\s*([\d,]+(?:\.\d{2})?)/i',
            '/USD\s*([\d,]+(?:\.\d{2})?)/i',
            
            // Price labels
            '/Price:?\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)/i',
            '/Price:?\s*PKR\s*([\d,]+(?:\.\d{2})?)/i',
            '/Price:?\s*USD\s*([\d,]+(?:\.\d{2})?)/i',
            
            // Number after currency
            '/([\d,]+(?:\.\d{2})?)\s*Rs/i',
            '/([\d,]+(?:\.\d{2})?)\s*PKR/i',
            '/([\d,]+(?:\.\d{2})?)\s*USD/i',
            
            // Common ecommerce patterns
            '/data-price=["\']([\d,]+(?:\.\d{2})?)["\']/i',
            '/product_price["\']?:\s*["\']?([\d,]+(?:\.\d{2})?)/i',
            
            // Just look for numbers that could be prices
            '/(?<!\d)(\d{3,6}(?:\.\d{2})?)(?!\d)/', // 3-6 digits with optional decimals
            '/(?<!\d)(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)(?!\d)/' // Comma-separated thousands
        ];
        
        foreach ($patterns as $pattern) {
            if (preg_match_all($pattern, $text, $matches, PREG_SET_ORDER)) {
                foreach ($matches as $match) {
                    $priceStr = str_replace(',', '', $match[1]);
                    if ($this->isValidPrice($priceStr)) {
                        logMessage('DEBUG', "Matched price pattern: $pattern - Found: $priceStr");
                        return $priceStr;
                    }
                }
            }
        }
        
        return null;
    }
    
    /**
     * Validate price with more checks
     */
    public function isValidPrice($priceStr) {
        if (empty($priceStr)) {
            return false;
        }
        
        // Check if it's a numeric string
        if (!is_numeric(str_replace(',', '', $priceStr))) {
            return false;
        }
        
        $price = (float) str_replace(',', '', $priceStr);
        
        // Check reasonable price range for Pakistani ecommerce
        return $price >= 10 && $price <= 1000000;
    }
    
    /**
     * Consistent price formatting
     */
    public function formatPrice($priceStr) {
        $price = (float) str_replace(',', '', $priceStr);
        return number_format($price, 2, '.', '');
    }
    
    /**
     * Enhanced scraping with better error handling
     */
    public function scrapePrice($url) {
        if (empty($url)) {
            logMessage('ERROR', "Empty URL provided");
            return null;
        }
        
        try {
            logMessage('INFO', "Scraping price from: $url");
            
            $htmlContent = $this->fetchHtmlContent($url);
            if ($htmlContent === null) {
                logMessage('ERROR', "Failed to fetch content from URL: $url");
                return null;
            }
            
            $price = $this->extractPriceFromHtml($htmlContent, $url);
            
            // Only save HTML if debug mode is on and we failed to find a price
            if ($this->debugMode && !$price) {
                file_put_contents('naheed_last_page.html', $htmlContent);
                logMessage('DEBUG', "Saved page HTML to naheed_last_page.html for debugging");
            }
            
            if ($price) {
                logMessage('INFO', "✅ Found price: $price");
                return $price;
            }
            
            logMessage('WARNING', "No price found in page content");
            return null;
            
        } catch (Exception $e) {
            logMessage('ERROR', "Error scraping price: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Process CSV file and extract Naheed data
     */
    public function processCsv($csvFilePath) {
        logMessage('INFO', "Starting to process CSV file for Naheed...");
        try {
            if (!file_exists($csvFilePath)) {
                logMessage('ERROR', "CSV file not found: $csvFilePath");
                return;
            }
            
            $handle = fopen($csvFilePath, 'r');
            if (!$handle) {
                logMessage('ERROR', "Could not open CSV file: $csvFilePath");
                return;
            }
            
            $rows = [];
            while (($row = fgetcsv($handle)) !== false) {
                $rows[] = $row;
            }
            fclose($handle);
            
            if (count($rows) < 3) {
                logMessage('ERROR', "CSV file doesn't have enough rows");
                return;
            }
            
            // Initialize results structure
            $this->results = [];
            
            // Process each product row
            for ($rowIdx = 2; $rowIdx < count($rows); $rowIdx++) {
                $row = $rows[$rowIdx];
                if (count($row) < 6) {
                    continue;
                }
                
                $sku = $row[0];
                $myPrice = $row[1];
                $naheedLink = $row[4]; // Naheed link is in column 4 (index 4)
                
                if (empty($sku) || trim($sku) == '') {
                    continue;
                }
                
                $productData = [
                    'SKU' => $sku,
                    'my_price' => $myPrice,
                    'Naheed_price' => '',
                    'Naheed_link' => $naheedLink
                ];
                
                // Scrape Naheed price if link exists
                if (!empty($naheedLink) && trim($naheedLink) != '') {
                    if ($rowIdx > 3) {
                        sleep(5); // Rate limiting
                    }
                    logMessage('INFO', "Processing SKU: $sku for Naheed");
                    $price = $this->scrapePrice(trim($naheedLink));
                    if ($price) {
                        $productData['Naheed_price'] = $price;
                        logMessage('INFO', "✅ Naheed - $sku: $price");
                    } else {
                        $productData['Naheed_price'] = "None";
                        logMessage('WARNING', "❌ Naheed - $sku: No price found (set to None)");
                    }
                } else {
                    $productData['Naheed_price'] = "None";
                    logMessage('INFO', "⏭️ Naheed - $sku: No link provided (set to None)");
                }
                
                $this->results[] = $productData;
            }
            
            logMessage('INFO', "✅ Completed processing Naheed data!");
            logMessage('INFO', "Total products processed: " . count($this->results));
            
        } catch (Exception $e) {
            logMessage('ERROR', "Error processing CSV file: " . $e->getMessage());
        }
    }
    
    /**
     * Ensure that Naheed columns exist in the table, and add them if not present.
     */
    public function ensureNaheedColumns() {
        try {
            $conn = new mysqli("localhost", "root", "", "competitor_price_data", 3306);
            
            if ($conn->connect_error) {
                logMessage('ERROR', "Connection failed: " . $conn->connect_error);
                return;
            }
            
            // Get current columns
            $result = $conn->query("SHOW COLUMNS FROM unified_competitor_prices");
            $columns = [];
            while ($row = $result->fetch_assoc()) {
                $columns[] = $row['Field'];
            }
            
            // Add Naheed columns if missing
            if (!in_array('Naheed_price', $columns)) {
                $conn->query("ALTER TABLE unified_competitor_prices ADD COLUMN Naheed_price VARCHAR(50) AFTER my_price");
            }
            if (!in_array('Naheed_link', $columns)) {
                $conn->query("ALTER TABLE unified_competitor_prices ADD COLUMN Naheed_link TEXT AFTER Naheed_price");
            }
            
            $conn->close();
        } catch (Exception $e) {
            logMessage('ERROR', "Error ensuring Naheed columns: " . $e->getMessage());
        }
    }
    
    /**
     * Create MySQL table with only SKU, my_price if not exists
     */
    public function createMysqlTable() {
        try {
            logMessage('INFO', "Creating MySQL table...");
            $conn = new mysqli("localhost", "root", "", "", 3306);
            
            if ($conn->connect_error) {
                logMessage('ERROR', "Connection failed: " . $conn->connect_error);
                return;
            }
            
            // Create database if not exists
            $conn->query("CREATE DATABASE IF NOT EXISTS competitor_price_data");
            $conn->select_db("competitor_price_data");
            
            // Create table with only SKU and my_price if not exists
            $createTableQuery = "
                CREATE TABLE IF NOT EXISTS unified_competitor_prices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    SKU VARCHAR(255),
                    my_price VARCHAR(50)
                )
            ";
            $conn->query($createTableQuery);
            logMessage('INFO', "✅ MySQL table created successfully!");
            $conn->close();
        } catch (Exception $e) {
            logMessage('ERROR', "Error creating MySQL table: " . $e->getMessage());
        }
    }
    
    /**
     * Save Naheed results to MySQL (insert new rows or update only Naheed columns)
     */
    public function saveToMysql() {
        try {
            logMessage('INFO', "Saving Naheed data to MySQL...");
            // Ensure columns exist
            $this->ensureNaheedColumns();
            
            // Connect to MySQL
            $conn = new mysqli("localhost", "root", "", "competitor_price_data", 3306);
            
            if ($conn->connect_error) {
                logMessage('ERROR', "Connection failed: " . $conn->connect_error);
                return;
            }
            
            // Insert or update data for each product
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
                    // Update only Naheed columns for existing row
                    $updateQuery = "
                        UPDATE unified_competitor_prices 
                        SET Naheed_price = ?, Naheed_link = ?, my_price = ?
                        WHERE SKU = ?
                    ";
                    $stmt = $conn->prepare($updateQuery);
                    $stmt->bind_param("ssss", 
                        $product['Naheed_price'],
                        $product['Naheed_link'],
                        $product['my_price'],
                        $product['SKU']
                    );
                    $stmt->execute();
                    $stmt->close();
                    logMessage('INFO', "Updated Naheed data for SKU: " . $product['SKU']);
                } else {
                    // Insert new row with only Naheed columns
                    $insertQuery = "
                        INSERT INTO unified_competitor_prices 
                        (SKU, my_price, Naheed_price, Naheed_link)
                        VALUES (?, ?, ?, ?)
                    ";
                    $stmt = $conn->prepare($insertQuery);
                    $stmt->bind_param("ssss", 
                        $product['SKU'],
                        $product['my_price'],
                        $product['Naheed_price'],
                        $product['Naheed_link']
                    );
                    $stmt->execute();
                    $stmt->close();
                    logMessage('INFO', "Inserted new row for SKU: " . $product['SKU']);
                }
            }
            
            logMessage('INFO', "✅ Saved " . count($this->results) . " Naheed products to MySQL!");
            $conn->close();
        } catch (Exception $e) {
            logMessage('ERROR', "Error saving to MySQL: " . $e->getMessage());
        }
    }
    
    /**
     * Save Naheed results to CSV file
     */
    public function saveToCsv($outputFile = 'naheed.csv') {
        try {
            logMessage('INFO', "Saving Naheed data to CSV: $outputFile");
            
            // Prepare CSV headers
            $headers = ["SKU", "my_price", "Naheed_price", "Naheed_link"];
            
            // Write to CSV
            $handle = fopen($outputFile, 'w');
            if (!$handle) {
                logMessage('ERROR', "Could not create CSV file: $outputFile");
                return;
            }
            
            // Write headers
            fputcsv($handle, $headers);
            
            // Write data rows
            foreach ($this->results as $row) {
                fputcsv($handle, [
                    $row['SKU'],
                    $row['my_price'],
                    $row['Naheed_price'],
                    $row['Naheed_link']
                ]);
            }
            
            fclose($handle);
            logMessage('INFO', "✅ Saved " . count($this->results) . " Naheed products to CSV!");
        } catch (Exception $e) {
            logMessage('ERROR', "Error saving to CSV: " . $e->getMessage());
        }
    }
}

/**
 * Main function to run the Naheed price scraping process
 */
function main() {
    echo "Naheed Competitor Price Scraper\n";
    echo str_repeat("=", 50) . "\n";
    echo "📋 Processing: Naheed competitor only\n";
    echo "📊 Output: naheed.csv\n";
    echo "🗄️  Database: Shared MySQL table\n";
    echo str_repeat("=", 50) . "\n";
    
    // Initialize scraper with debug mode off
    $scraper = new NaheedPriceScraper(false);
    
    // Process the CSV file
    $csvFile = "Cartpk competitors link(Developer Sample File).csv";
    $scraper->processCsv($csvFile);
    
    // Only proceed if we have results
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
        
        echo "\n🎉 Naheed scraping completed successfully!\n";
        echo "📊 Total products processed: " . count($scraper->results) . "\n";
        echo "📁 Data saved to:\n";
        echo "   - MySQL table: unified_competitor_prices\n";
        echo "   - CSV file: naheed.csv\n";
    } else {
        echo "\n❌ No Naheed data to save!\n";
    }
}

// Run the main function
main();
