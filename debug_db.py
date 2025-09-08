#!/usr/bin/env python3
"""Debug script to check database state and diagnose scraper issues"""

import pymysql
import sys
from datetime import datetime

def connect_db():
    """Connect to the database"""
    try:
        conn = pymysql.connect(
            host='192.168.0.90',
            port=3306,
            user='nssm',
            password='YKNOgu4We2pdKZ',
            database='nssm',
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def check_tables():
    """Check what tables exist"""
    conn = connect_db()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("📋 Tables in database:")
            for table in tables:
                print(f"  - {table[0]}")
    finally:
        conn.close()

def check_posts_table():
    """Check posts table structure and contents"""
    conn = connect_db()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            # Check table structure
            print("\n📊 Posts table structure:")
            cursor.execute("DESCRIBE posts")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM posts")
            count = cursor.fetchone()[0]
            print(f"\n📈 Posts table has {count} rows")
            
            # Show sample data if any
            if count > 0:
                cursor.execute("SELECT id, forum_id, post_id, ticker, author, timestamp FROM posts LIMIT 5")
                rows = cursor.fetchall()
                print("\n📝 Sample posts:")
                for row in rows:
                    print(f"  ID: {row[0]}, Forum: {row[1]}, PostID: {row[2]}, Ticker: {row[3]}, Author: {row[4]}")
    finally:
        conn.close()

def check_forums():
    """Check forums table"""
    conn = connect_db()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, url FROM forums")
            forums = cursor.fetchall()
            print("\n🏢 Forums in database:")
            for forum in forums:
                print(f"  ID: {forum[0]}, Name: {forum[1]}, URL: {forum[2]}")
    finally:
        conn.close()

def main():
    print("🔍 Debugging NSSM database state...")
    check_tables()
    check_forums()
    check_posts_table()

if __name__ == "__main__":
    main()