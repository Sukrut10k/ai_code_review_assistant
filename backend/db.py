import os
from typing import List, Optional, Dict, Any

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "code_review_db")


def get_connection(with_db: bool = True):
    """
    Create and return a new MySQL connection.
    If with_db is False, connects without specifying database (for initial creation).
    """
    if with_db:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
    else:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
        )


def init_db():
    """
    Initialize the database and the 'reviews' table if they don't exist.
    Also ensure all required columns exist.
    """
    try:
        # Create database if not exists
        conn = get_connection(with_db=False)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.close()
        conn.close()

        #Create table if not exists
        conn = get_connection(with_db=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filenames TEXT NOT NULL,
                summary TEXT NOT NULL,
                details LONGTEXT NOT NULL,
                raw_response LONGTEXT
            )
            """
        )
        conn.commit()

        #Ensure issues_json column exists
        try:
            cursor.execute(
                "ALTER TABLE reviews ADD COLUMN issues_json LONGTEXT"
            )
            conn.commit()
            print("[DB] Added issues_json column to reviews table.")
        except Error:
            # if Column already exists then ignore
            pass

        #Add new columns for enhanced features
        new_columns = [
            ("quality_score", "FLOAT DEFAULT 0"),
            ("metrics_json", "LONGTEXT"),
            ("strengths_json", "LONGTEXT"),
        ]
        
        for col_name, col_def in new_columns:
            try:
                cursor.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_def}")
                conn.commit()
                print(f"[DB] Added {col_name} column to reviews table.")
            except Error:
                # if Column already exists then ignore
                pass

        cursor.close()
        conn.close()
        print("[DB] Database and 'reviews' table are ready.")
    except Error as e:
        print(f"[DB] Error during init_db: {e}")


def insert_review(
    filenames: List[str],
    summary: str,
    details: str,
    raw_response: Optional[str] = None,
    issues_json: Optional[str] = None,
    quality_score: float = 0.0,
    metrics_json: Optional[str] = None,
    strengths_json: Optional[str] = None,
) -> int:
    """
    Insert a new review into the 'reviews' table and return its ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection(with_db=True)
        cursor = conn.cursor()

        filenames_str = ", ".join(filenames)

        sql = """
            INSERT INTO reviews (filenames, summary, details, raw_response, issues_json, 
                               quality_score, metrics_json, strengths_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (filenames_str, summary, details, raw_response, issues_json,
                           quality_score, metrics_json, strengths_json))
        conn.commit()

        review_id = cursor.lastrowid
        return review_id
    except Error as e:
        print(f"[DB] Error in insert_review: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def fetch_recent_reviews(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch the most recent reviews, limited by 'limit'.
    Returns a list of dicts.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection(with_db=True)
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT id, created_at, filenames, summary, quality_score
            FROM reviews
            ORDER BY created_at DESC
            LIMIT %s
        """
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print(f"[DB] Error in fetch_recent_reviews: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def fetch_review_by_id(review_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch full review details by ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection(with_db=True)
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT id, created_at, filenames, summary, details, raw_response, 
                   issues_json, quality_score, metrics_json, strengths_json
            FROM reviews
            WHERE id = %s
        """
        cursor.execute(sql, (review_id,))
        row = cursor.fetchone()
        return row
    except Error as e:
        print(f"[DB] Error in fetch_review_by_id: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()