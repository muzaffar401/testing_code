import pymysql
from pymysql import cursors
import csv
import traceback

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'competitor_price_data',
    'port': 3306
}

COMPETITORS = ['Cartpk', 'Diamond', 'Naheed', 'Metro']

COMPARISON_TABLE = 'competitor_price_comparison'
OUTPUT_CSV = 'competitor_price_comparison.csv'


def fetch_data():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(cursors.DictCursor)
    cursor.execute('SELECT * FROM unified_competitor_prices')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def compare_prices(row):
    results = {}
    try:
        my_price = float(row['my_price']) if row['my_price'] not in (None, '', 'None') else None
    except Exception:
        my_price = None
    for comp in COMPETITORS:
        comp_price_key = f'{comp}_price'
        try:
            comp_price = float(row[comp_price_key]) if row[comp_price_key] not in (None, '', 'None') else None
        except Exception:
            comp_price = None
        if my_price is not None and comp_price is not None:
            if my_price == comp_price:
                results[f'compare_{comp.lower()}'] = ''
            elif my_price > comp_price:
                results[f'compare_{comp.lower()}'] = 'high'
            else:
                results[f'compare_{comp.lower()}'] = 'low'
        else:
            results[f'compare_{comp.lower()}'] = ''
    return results

def write_csv(data):
    headers = ['SKU', 'my_price', 'competitor', 'competitor_price', 'comparison']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for comp in COMPETITORS:
            for row in data:
                writer.writerow({
                    'SKU': row['SKU'],
                    'my_price': row.get('my_price', ''),
                    'competitor': comp,
                    'competitor_price': row.get(f'{comp}_price', ''),
                    'comparison': row.get(f'compare_{comp.lower()}', '')
                })

def save_to_mysql(data):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    columns = [
        'id INT AUTO_INCREMENT PRIMARY KEY',
        'SKU VARCHAR(255)',
        'my_price VARCHAR(50)',
        'competitor VARCHAR(50)',
        'competitor_price VARCHAR(50)',
        'comparison VARCHAR(10)'
    ]
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {COMPARISON_TABLE} (
            {', '.join(columns)}
        )
    """
    cursor.execute(f"DROP TABLE IF EXISTS {COMPARISON_TABLE}")
    cursor.execute(create_table_sql)
    insert_cols = ['SKU', 'my_price', 'competitor', 'competitor_price', 'comparison']
    placeholders = ','.join(['%s'] * len(insert_cols))
    insert_sql = f"INSERT INTO {COMPARISON_TABLE} ({', '.join(insert_cols)}) VALUES ({placeholders})"
    for comp in COMPETITORS:
        for row in data:
            values = [
                row['SKU'],
                row.get('my_price', ''),
                comp,
                row.get(f'{comp}_price', ''),
                row.get(f'compare_{comp.lower()}', '')
            ]
            cursor.execute(insert_sql, values)
    conn.commit()
    cursor.close()
    conn.close()

def main():
    try:
        print('Fetching data from MySQL...')
        rows = fetch_data()
        print(f'Fetched {len(rows)} rows.')
        # Compare prices
        for row in rows:
            row.update(compare_prices(row))
        # Write to CSV
        print('Writing comparison CSV...')
        write_csv(rows)
        print(f'Comparison CSV saved as {OUTPUT_CSV}')
        # Save to MySQL
        print('Saving comparison data to MySQL...')
        save_to_mysql(rows)
        print(f'Comparison data saved to table: {COMPARISON_TABLE}')
    except Exception as e:
        print('Error:', e)
        traceback.print_exc()

if __name__ == '__main__':
    main() 