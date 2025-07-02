import mysql.connector
import sys

print("Simple MySQL Test")
print("=" * 20)

try:
    print("Attempting to connect...")
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=""
    )
    print("Connection successful!")
    
    if connection.is_connected():
        cursor = connection.cursor()
        cursor.execute("SELECT 'Hello MySQL!' as message")
        result = cursor.fetchone()
        print(f"Test query result: {result[0]}")
        
        cursor.close()
        connection.close()
        print("Connection closed.")
    else:
        print("Connection failed!")
        
except mysql.connector.Error as err:
    print(f"MySQL Error: {err}")
    print(f"Error Code: {err.errno}")
    print(f"SQL State: {err.sqlstate}")
    print(f"Error Message: {err.msg}")
    
except Exception as e:
    print(f"General Error: {e}")
    print(f"Error Type: {type(e)}")
    
finally:
    print("Test completed.") 