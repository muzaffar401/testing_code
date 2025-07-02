import mysql.connector
from mysql.connector import Error
import socket
import sys

print("🔍 Detailed MySQL Connection Debug")
print("=" * 50)

# Test 1: Port check
print("1. Port 3306 status:")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('localhost', 3306))
    sock.close()
    
    if result == 0:
        print("   ✅ Port 3306 is open and accessible")
    else:
        print(f"   ❌ Port 3306 is not accessible (error code: {result})")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error testing port: {e}")
    sys.exit(1)

# Test 2: Try different connection parameters
print("\n2. Testing MySQL connections with different parameters:")

connection_configs = [
    {"host": "localhost", "user": "root", "password": "", "port": 3306},
    {"host": "127.0.0.1", "user": "root", "password": "", "port": 3306},
    {"host": "localhost", "user": "root", "password": "", "port": 3306, "auth_plugin": "mysql_native_password"},
    {"host": "localhost", "user": "root", "password": "", "port": 3306, "autocommit": True},
]

for i, config in enumerate(connection_configs, 1):
    print(f"\n   Test {i}: {config}")
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            print(f"   ✅ SUCCESS with config {i}!")
            
            # Get server info
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"   📊 MySQL Version: {version[0] if version else 'Unknown'}")
            
            cursor.execute("SELECT USER()")
            user = cursor.fetchone()
            print(f"   👤 Connected as: {user[0] if user else 'Unknown'}")
            
            cursor.close()
            conn.close()
            print("   ✅ Connection closed successfully!")
            
            # If we get here, connection worked - let's run the original script
            print("\n🎉 MySQL connection successful! Now running your original script...")
            print("=" * 50)
            
            # Import and run the original script logic
            import mysql.connector
            from mysql.connector import Error
            
            try:
                conn = mysql.connector.connect(**config)
                if conn.is_connected():
                    cursor = conn.cursor()
                    
                    # Create database
                    print("📊 Creating database 'myshop'...")
                    cursor.execute("CREATE DATABASE IF NOT EXISTS myshop")
                    print("✅ Database 'myshop' created/verified!")
                    
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
                    
                    # Insert data
                    print("📝 Inserting sample data...")
                    cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Laptop", 80000))
                    cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Mouse", 1500))
                    conn.commit()
                    print("✅ Sample data inserted successfully!")
                    
                    # Fetch and display data
                    print("🔍 Fetching data from database...")
                    cursor.execute("SELECT * FROM products")
                    rows = cursor.fetchall()
                    
                    print("📦 Product List:")
                    for row in rows:
                        print(f"   ID: {row[0]}, Name: {row[1]}, Price: Rs. {row[2]}")
                    
                    cursor.close()
                    conn.close()
                    print("✅ All operations completed successfully!")
                    
            except Error as e:
                print(f"❌ Error in main script: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
            
            sys.exit(0)
            
        else:
            print(f"   ❌ Failed to connect with config {i}")
            
    except Error as e:
        print(f"   ❌ MySQL Error with config {i}: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error with config {i}: {e}")

print("\n❌ All connection attempts failed!")
print("\n🔧 Troubleshooting steps:")
print("1. Make sure XAMPP is running")
print("2. Check XAMPP Control Panel - MySQL should show 'Running'")
print("3. Try restarting MySQL service in XAMPP")
print("4. Check if there are any firewall issues")
print("5. Verify MySQL root user has no password")
print("6. Try connecting via phpMyAdmin to test MySQL manually") 