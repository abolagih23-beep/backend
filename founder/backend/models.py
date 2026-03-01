# models.py
from db import execute_query

def create_tables():
    # Users table
    execute_query("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        role VARCHAR(10) NOT NULL,
        password VARCHAR(255) NOT NULL
    )
    """)

    # Products table
    execute_query("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        cp NUMERIC(10,2) NOT NULL,
        sp NUMERIC(10,2) NOT NULL,
        quantity INT NOT NULL,
        category VARCHAR(50)
    )
    """)

    # Sales table
    execute_query("""
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        product_id INT REFERENCES products(id),
        quantity INT NOT NULL,
        staff_id INT REFERENCES users(id),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

if __name__ == "__main__":
    create_tables()
    print("✅ All tables created successfully!")