import requests
from bs4 import BeautifulSoup
import re

def test_json_extraction():
    """Test JSON extraction from Metro pages"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    url = "https://www.metro-online.pk/detail/grocery/tea-and-coffee/tea/tapal-danedar-black-tea-900gm/12631638"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Page content length: {len(response.text)} characters")
        
        # Find all script tags
        scripts = soup.find_all('script')
        print(f"\nFound {len(scripts)} script tags")
        
        for i, script in enumerate(scripts):
            script_text = script.get_text()
            if script_text:
                print(f"\nScript {i+1} (length: {len(script_text)} chars):")
                print(f"   First 200 chars: {script_text[:200]}...")
                
                # Check if this script contains price data
                if '"price"' in script_text and '"sell_price"' in script_text:
                    print(f"   *** CONTAINS PRICE DATA! ***")
                    
                    # Extract price from JSON
                    price_match = re.search(r'"price":(\d+(?:\.\d+)?)', script_text)
                    sell_price_match = re.search(r'"sell_price":(\d+(?:\.\d+)?)', script_text)
                    
                    if sell_price_match:
                        price = sell_price_match.group(1)
                        print(f"   Found sell_price: {price}")
                    
                    if price_match:
                        price = price_match.group(1)
                        print(f"   Found price: {price}")
                    
                    # Show more context around the price data
                    price_context = re.search(r'\{[^{}]*"price"[^{}]*\}', script_text)
                    if price_context:
                        print(f"   Price context: {price_context.group(0)[:300]}...")
                else:
                    print(f"   No price data found")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_json_extraction() 