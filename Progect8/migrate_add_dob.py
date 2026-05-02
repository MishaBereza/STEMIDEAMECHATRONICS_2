#!/usr/bin/env python3
"""
Migration script to add date_of_birth column to User table.
Run this once after deploying the new model changes.
"""

import sqlite3
import os
from pathlib import Path

def add_date_of_birth_column():
    """Add the date_of_birth column to the user table if it doesn't exist."""
    # Get database path from .env
    env_file = Path(__file__).parent / '.env'
    db_path = 'data.db'  # default

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    url = line.split('=', 1)[1].strip()
                    if url.startswith('sqlite:///'):
                        db_path = url[10:]  # remove sqlite:///
                    break

    print(f"Using database: {db_path}")

    # Connect to SQLite directly
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'date_of_birth' not in columns:
        print("Adding date_of_birth column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN date_of_birth DATE")
        conn.commit()
        print("Column added successfully!")
    else:
        print("date_of_birth column already exists.")

    conn.close()

if __name__ == '__main__':
    add_date_of_birth_column()