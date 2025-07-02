import pymysql
import sys

print("PyMySQL Connection Test")
print("=" * 25)

try:
    print("Attempting to connect with PyMySQL...")
    connection = pymysql.connect(
        host="localhost",
        user="root",
        password="",
        port=3306
    )
    print("✅ Connection successful!")
    
    with connection.cursor() as cursor:
        # Test basic query
        cursor.execute("SELECT 'Hello MySQL!' as message")
        result = cursor.fetchone()
        print(f"📊 Test query result: {result[0]}")
        
        # Get MySQL version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"📋 MySQL Version: {version[0]}")
        
        # List databases
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        print("📁 Existing databases:")
        for db in databases:
            print(f"   - {db[0]}")
        
        # Create database if not exists
        print("\n📊 Creating database 'myshop'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS myshop")
        print("✅ Database 'myshop' created/verified!")
        
        # Use the database
        cursor.execute("USE myshop")
        print("✅ Using database 'myshop'")
        
        # Create table
        print("📋 Creating table 'products'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                price DECIMAL(10,2)
            )
        """)
        print("✅ Table 'products' created/verified!")
        
        # Insert sample data
        print("📝 Inserting sample data...")
        cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Laptop", 80000))
        cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Mouse", 1500))
        connection.commit()
        print("✅ Sample data inserted successfully!")
        
        # Fetch and display data
        print("🔍 Fetching data from database...")
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        
        print("📦 Product List:")
        for row in rows:
            print(f"   ID: {row[0]}, Name: {row[1]}, Price: Rs. {row[2]}")
    
    connection.close()
    print("✅ Connection closed successfully!")
    print("\n🎉 All operations completed successfully!")
    
except pymysql.Error as err:
    print(f"❌ PyMySQL Error: {err}")
    print(f"Error Code: {err.args[0] if err.args else 'Unknown'}")
    print(f"Error Message: {err.args[1] if len(err.args) > 1 else 'Unknown'}")
    
except Exception as e:
    print(f"❌ General Error: {e}")
    print(f"Error Type: {type(e)}")
    
finally:
    print("Test completed.") 