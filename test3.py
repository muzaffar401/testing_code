import pymysql

# Connect karo MySQL server se (XAMPP ke root user ke zariye)
print("🔌 Attempting to connect to MySQL...")
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    port=3306
)

print("✅ Successfully connected to MySQL!")
cursor = conn.cursor()

# Step 1: Agar database nahi bana to banao
print("📊 Creating database 'myshop'...")
cursor.execute("CREATE DATABASE IF NOT EXISTS myshop")
print("✅ Database 'myshop' created/verified!")

cursor.execute("USE myshop")
print("✅ Using database 'myshop'")

# Step 2: Agar table nahi bana to banao
print("📋 Creating table 'products'...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        price DECIMAL(10,2)
    )
""")
print("✅ Table 'products' created/verified!")

# Step 3: Sample data insert karo
print("📝 Inserting sample data...")
cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Laptop", 80000))
cursor.execute("INSERT INTO products (name, price) VALUES (%s, %s)", ("Mouse", 1500))
conn.commit()
print("✅ Sample data inserted successfully!")

# Step 4: Data fetch karke print karo
print("🔍 Fetching data from database...")
cursor.execute("SELECT * FROM products")
rows = cursor.fetchall()

print("📦 Product List:")
for row in rows:
    print(f"ID: {row[0]}, Name: {row[1]}, Price: Rs. {row[2]}")

# Close
cursor.close()
conn.close()
print("✅ Connection closed successfully!")
