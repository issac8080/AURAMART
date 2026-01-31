"""
Convert Flipkart CSV to products.json format
"""
import csv
import json
import re
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "flipkart_products.csv"
JSON_PATH = Path(__file__).parent / "data" / "products.json"

def clean_price(price_str):
    """Extract numeric price from string"""
    if not price_str or price_str == "":
        return 0.0
    try:
        # Remove commas and convert to float
        return float(str(price_str).replace(",", ""))
    except:
        return 0.0

def clean_rating(rating_str):
    """Extract numeric rating"""
    if not rating_str or rating_str == "No rating available":
        return 4.0  # Default rating
    try:
        return float(rating_str)
    except:
        return 4.0

def is_product_specific(category_name):
    """Check if category name looks like a specific product"""
    # Indicators of product-specific names
    indicators = [
        "LCD", "LED", "PIR", "Wireless", "Analog", "Digital",
        "Series", "Model", "Type", "Version",
        "Black", "White", "Red", "Blue", "Green", "Gold", "Silver", "Orange",
        "Synthetic", "Leather", "Cotton", "Silk",
        "Rose", "Lace", "Crystal",
        "Clutch", "Mixer", "Sensor", "Controller", "Pump",
        "8520", "502", "YIT-", "Super", "Blooms"
    ]
    
    for indicator in indicators:
        if indicator.lower() in category_name.lower():
            return True
    
    # If category name is too long, it's likely product-specific
    if len(category_name) > 40:
        return True
    
    return False

def extract_category(category_tree):
    """Extract and map to general category"""
    if not category_tree:
        return "General"
    
    # Category mapping to general categories
    category_map = {
        "clothing": "Clothing & Fashion",
        "women": "Clothing & Fashion",
        "men": "Clothing & Fashion",
        "apparel": "Clothing & Fashion",
        "footwear": "Footwear",
        "shoes": "Footwear",
        "sandal": "Footwear",
        "boot": "Footwear",
        "furniture": "Furniture",
        "sofa": "Furniture",
        "bed": "Furniture",
        "table": "Furniture",
        "chair": "Furniture",
        "home": "Home & Kitchen",
        "kitchen": "Home & Kitchen",
        "appliances": "Home & Kitchen",
        "cookware": "Home & Kitchen",
        "tableware": "Home & Kitchen",
        "electronics": "Electronics",
        "mobile": "Electronics",
        "computer": "Electronics",
        "laptop": "Electronics",
        "camera": "Electronics",
        "audio": "Electronics",
        "jewellery": "Jewellery & Accessories",
        "jewelry": "Jewellery & Accessories",
        "watches": "Jewellery & Accessories",
        "accessories": "Accessories",
        "bags": "Bags & Luggage",
        "luggage": "Bags & Luggage",
        "handbag": "Bags & Luggage",
        "beauty": "Beauty & Personal Care",
        "health": "Beauty & Personal Care",
        "personal care": "Beauty & Personal Care",
        "cosmetic": "Beauty & Personal Care",
        "fragrance": "Beauty & Personal Care",
        "sports": "Sports & Fitness",
        "fitness": "Sports & Fitness",
        "exercise": "Sports & Fitness",
        "gym": "Sports & Fitness",
        "toys": "Toys & Baby Products",
        "baby": "Toys & Baby Products",
        "kids": "Toys & Baby Products",
        "infant": "Toys & Baby Products",
        "books": "Books & Media",
        "automotive": "Automotive",
        "car": "Automotive",
        "vehicle": "Automotive",
        "tools": "Tools & Hardware",
        "hardware": "Tools & Hardware",
        "office": "Office Supplies",
        "stationery": "Office Supplies",
        "pet": "Pet Supplies",
        "sunglasses": "Sunglasses",
        "eyewear": "Sunglasses",
    }
    
    try:
        # Parse the category tree
        categories = eval(category_tree)[0].lower()
        
        # Check each keyword in our mapping (prioritize longer matches)
        matched_cat = None
        max_len = 0
        for keyword, general_cat in category_map.items():
            if keyword in categories and len(keyword) > max_len:
                matched_cat = general_cat
                max_len = len(keyword)
        
        if matched_cat:
            return matched_cat
        
        # If no match, try to extract first meaningful category
        parts = eval(category_tree)[0].split(">>")
        if len(parts) > 0:
            first_cat = parts[0].strip()
            # Check if it's product-specific
            if not is_product_specific(first_cat) and len(first_cat) < 50:
                return first_cat
        
        return "General"
    except:
        return "General"

def extract_image(image_str):
    """Extract first image URL from image array"""
    if not image_str:
        return ""
    try:
        images = eval(image_str)
        if isinstance(images, list) and len(images) > 0:
            return images[0]
        return ""
    except:
        return ""

def convert_csv_to_json(limit=1000):
    """Convert CSV to JSON format"""
    products = []
    category_stats = {}
    
    print(f"Reading CSV from: {CSV_PATH}")
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i >= limit:
                break
                
            try:
                # Extract and clean data
                product_id = row.get('pid', row.get('uniq_id', f'prod_{i}'))
                name = row.get('product_name', 'Unknown Product')
                category = extract_category(row.get('product_category_tree', ''))
                
                # Track category usage
                category_stats[category] = category_stats.get(category, 0) + 1
                
                # Get price (prefer discounted, fallback to retail)
                discounted = clean_price(row.get('discounted_price', ''))
                retail = clean_price(row.get('retail_price', ''))
                price = discounted if discounted > 0 else retail
                
                if price == 0:
                    price = 999.0  # Default price
                
                rating = clean_rating(row.get('product_rating', ''))
                image = extract_image(row.get('image', ''))
                brand = row.get('brand', 'Generic')
                description = row.get('description', '')[:500]  # Limit description
                
                product = {
                    "id": product_id,
                    "name": name,
                    "category": category,
                    "price": price,
                    "rating": rating,
                    "review_count": 100,  # Default review count
                    "image_url": image,
                    "brand": brand,
                    "description": description,
                    "colors": [],
                    "in_stock": True
                }
                
                products.append(product)
                
                if (i + 1) % 100 == 0:
                    print(f"Processed {i + 1} products...")
                    
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                continue
    
    print(f"\nTotal products converted: {len(products)}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count} products")
    
    # Write to JSON
    print(f"\nWriting to: {JSON_PATH}")
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    print("[OK] Conversion complete!")
    return len(products)

if __name__ == "__main__":
    count = convert_csv_to_json(limit=1000)  # Convert first 1000 products
    print(f"\n{count} products saved to products.json")
