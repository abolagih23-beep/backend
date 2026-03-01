# db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    return conn

def execute_query(query, values=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()
    finally:
        cur.close()
        conn.close()

def fetch_one(query, values=None):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, values)
        result = cur.fetchone()
        return result
    finally:
        cur.close()
        conn.close()

def fetch_all(query, values=None):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, values)
        result = cur.fetchall()
        return result
    finally:
        cur.close()
        conn.close()