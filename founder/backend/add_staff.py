# add_staff.py
from utils import hash_password
from db import execute_query

def add_staff(name: str, plain_password: str):
    hashed = hash_password(plain_password)
    execute_query(
        "INSERT INTO users (name, role, password) VALUES (%s, %s, %s)",
        (name, "staff", hashed)
    )
    print(f"Staff '{name}' added successfully.")

# Example usage: dynamically add staff
staff_list = [
    ("Alice", "alice123"),
    ("Bob", "bob123"),
    ("Charlie", "charlie123"),
    ("David", "david123"),
    ("Eva", "eva123")
]

for name, pwd in staff_list:
    add_staff(name, pwd)