import mysql.connector
from mysql.connector import Error
import socket

def test_mysql_connection():
    print("🔍 MySQL Connection Test")
    print("=" * 40)
    
    # Test 1: Check if port 3306 is open
    print("1. Testing if MySQL port (3306) is accessible...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 3306))
        sock.close()
        
        if result == 0:
            print("✅ Port 3306 is open - MySQL might be running")
        else:
            print("❌ Port 3306 is closed - MySQL is not running")
            print("   Please start XAMPP and ensure MySQL service is running")
            return False
    except Exception as e:
        print(f"❌ Error testing port: {e}")
        return False
    
    # Test 2: Try to connect to MySQL
    print("\n2. Attempting to connect to MySQL...")
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            port=3306
        )
        
        if conn.is_connected():
            print("✅ Successfully connected to MySQL!")
            
            # Get MySQL version
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"📊 MySQL Version: {version[0]}")
            
            # List existing databases
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print("📁 Existing databases:")
            for db in databases:
                print(f"   - {db[0]}")
            
            cursor.close()
            conn.close()
            print("✅ Connection closed successfully!")
            return True
        else:
            print("❌ Failed to connect to MySQL!")
            return False
            
    except Error as e:
        print(f"❌ MySQL Connection Error: {e}")
        print("\n🔧 Common solutions:")
        print("1. Start XAMPP Control Panel")
        print("2. Click 'Start' next to MySQL")
        print("3. Make sure MySQL is running on port 3306")
        print("4. Check if root user has no password (or update password)")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_mysql_connection() 