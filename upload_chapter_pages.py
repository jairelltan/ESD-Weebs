import os
import mysql.connector
from mysql.connector import Error
import re

# Database configuration for chapter database
chapter_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'chapter_db'
}

# Database configuration for page database
page_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'page_db'
}

def get_chapter_db_connection():
    try:
        conn = mysql.connector.connect(**chapter_db_config)
        print("Chapter database connection successful")
        return conn
    except Error as e:
        print(f"Error connecting to chapter database: {e}")
        return None

def get_page_db_connection():
    try:
        conn = mysql.connector.connect(**page_db_config)
        print("Page database connection successful")
        return conn
    except Error as e:
        print(f"Error connecting to page database: {e}")
        return None

def get_chapter_id(cursor, comic_id, chapter_number):
    cursor.execute("""
        SELECT chapter_id 
        FROM chapter 
        WHERE comic_id = %s AND chapter_number = %s
    """, (comic_id, chapter_number))
    result = cursor.fetchone()
    return result[0] if result else None

def get_comic_id(cursor, comic_name):
    cursor.execute("""
        SELECT comic_id 
        FROM comic_db.comic 
        WHERE comic_name = %s
    """, (comic_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def extract_chapter_number(chapter_folder):
    # Try different patterns to extract chapter number
    
    # Pattern 1: "Chapter X" or "Chapter X - Title"
    match = re.search(r'Chapter (\d+)', chapter_folder)
    if match:
        return int(match.group(1))
    
    # Pattern 2: "Ch.XXXX" format (with leading zeros)
    match = re.search(r'Ch\.0*(\d+)', chapter_folder)
    if match:
        return int(match.group(1))
    
    # Pattern 3: Just the number itself
    match = re.search(r'(\d+)', chapter_folder)
    if match:
        return int(match.group(1))
    
    return None

def upload_pages(chapter_conn, page_conn, comic_name, chapter_folder, files):
    try:
        chapter_cursor = chapter_conn.cursor()
        page_cursor = page_conn.cursor()
        
        # Get comic_id
        comic_id = get_comic_id(chapter_cursor, comic_name)
        if not comic_id:
            print(f"Comic not found: {comic_name}")
            return
        
        # Get chapter number from folder name
        chapter_number = extract_chapter_number(chapter_folder)
        if not chapter_number:
            print(f"Could not extract chapter number from: {chapter_folder}")
            return
        
        # Get chapter_id
        chapter_id = get_chapter_id(chapter_cursor, comic_id, chapter_number)
        if not chapter_id:
            print(f"Chapter not found: {comic_name} Chapter {chapter_number}")
            return
        
        print(f"Processing {comic_name} Chapter {chapter_number} ({len(files)} pages)")
        
        # Sort files numerically (to handle 01.jpg, 02.jpg, etc. correctly)
        files.sort(key=lambda x: int(re.search(r'(\d+)', x).group(1)))
        
        # Insert each page
        for page_number, filename in enumerate(files, 1):
            file_path = os.path.join('Chapters', comic_name, chapter_folder, filename)
            
            # Read the image file
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Check if page already exists in the new page table
            page_cursor.execute("""
                SELECT page_id 
                FROM page 
                WHERE comic_id = %s AND chapter_id = %s AND page_number = %s
            """, (comic_id, chapter_id, page_number))
            
            if page_cursor.fetchone():
                # Update existing page
                page_cursor.execute("""
                    UPDATE page 
                    SET page_image = %s 
                    WHERE comic_id = %s AND chapter_id = %s AND page_number = %s
                """, (image_data, comic_id, chapter_id, page_number))
            else:
                # Insert new page
                page_cursor.execute("""
                    INSERT INTO page (comic_id, chapter_id, page_number, page_image)
                    VALUES (%s, %s, %s, %s)
                """, (comic_id, chapter_id, page_number, image_data))
            
            print(f"  Uploaded page {page_number}/{len(files)}")
        
        page_conn.commit()
        print(f"Successfully uploaded all pages for {comic_name} Chapter {chapter_number}")
        
    except Error as e:
        print(f"Error uploading pages: {e}")
        page_conn.rollback()

def main():
    chapter_conn = get_chapter_db_connection()
    page_conn = get_page_db_connection()
    
    if not chapter_conn or not page_conn:
        print("Failed to connect to databases.")
        if chapter_conn:
            chapter_conn.close()
        if page_conn:
            page_conn.close()
        return
    
    chapters_dir = 'Chapters'
    
    try:
        # Iterate through each comic folder
        for comic_name in os.listdir(chapters_dir):
            comic_path = os.path.join(chapters_dir, comic_name)
            if not os.path.isdir(comic_path):
                continue
            
            # Iterate through each chapter folder
            for chapter_folder in os.listdir(comic_path):
                chapter_path = os.path.join(comic_path, chapter_folder)
                if not os.path.isdir(chapter_path):
                    continue
                
                # Get all image files in the chapter folder
                files = [f for f in os.listdir(chapter_path) 
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                
                if files:
                    upload_pages(chapter_conn, page_conn, comic_name, chapter_folder, files)
    
    except Exception as e:
        print(f"Error processing folders: {e}")
    
    finally:
        if chapter_conn:
            chapter_conn.close()
        if page_conn:
            page_conn.close()

if __name__ == "__main__":
    main() 