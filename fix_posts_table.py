#!/usr/bin/env python3
"""Fix posts table by adding missing columns"""

import pymysql
import sys

def fix_posts_table():
    """Add missing post_id and url columns to posts table"""
    try:
        conn = pymysql.connect(
            host='192.168.0.90',
            port=3306,
            user='nssm',
            password='YKNOgu4We2pdKZ',
            database='nssm',
            charset='utf8mb4'
        )
        
        with conn.cursor() as cursor:
            print("🔧 Adding missing columns to posts table...")
            
            # Add post_id column
            try:
                cursor.execute("ALTER TABLE posts ADD COLUMN post_id VARCHAR(255)")
                print("✅ Added post_id column")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("ℹ️ post_id column already exists")
                else:
                    print(f"❌ Error adding post_id: {e}")
            
            # Add url column  
            try:
                cursor.execute("ALTER TABLE posts ADD COLUMN url VARCHAR(500)")
                print("✅ Added url column")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("ℹ️ url column already exists")
                else:
                    print(f"❌ Error adding url: {e}")
            
            # Create index
            try:
                cursor.execute("CREATE INDEX ix_posts_post_id ON posts (post_id)")
                print("✅ Created post_id index")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    print("ℹ️ post_id index already exists")
                else:
                    print(f"❌ Error creating index: {e}")
            
            # Update alembic version
            try:
                cursor.execute("UPDATE alembic_version SET version_num = '2b5c38e617c8'")
                print("✅ Updated alembic version")
            except Exception as e:
                print(f"❌ Error updating alembic version: {e}")
            
            conn.commit()
            print("🎉 Posts table fixed successfully!")
            
            # Check final structure
            cursor.execute("DESCRIBE posts")
            columns = cursor.fetchall()
            print("\n📊 Updated posts table structure:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
                
    except Exception as e:
        print(f"❌ Failed to fix posts table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_posts_table()