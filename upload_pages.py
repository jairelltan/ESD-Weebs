import os
import mysql.connector
from mysql.connector import Error
import re
import requests
import argparse

# Database configurations
chapter_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'chapter_db'
}

page_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'page_db'
}

comic_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'comic_db'
}

# API endpoints
CHAPTER_API_BASE = "http://localhost:5005/api/chapters"
PAGE_API_BASE = "http://localhost:5013/api/pages"  # Updated to port 5013

def get_db_connection(db_config):
    try:
        conn = mysql.connector.connect(**db_config)
        print(f"Database connection successful to {db_config['database']}")
        return conn
    except Error as e:
        print(f"Error connecting to database {db_config['database']}: {e}")
        return None

def get_chapter_info(chapter_id):
    """Get chapter information from the chapter API"""
    try:
        response = requests.get(f"{CHAPTER_API_BASE}/{chapter_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get chapter info: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error calling chapter API: {e}")
        return None

def get_chapter_id_from_db(cursor, comic_id, chapter_number):
    cursor.execute("""
        SELECT chapter_id 
        FROM chapter 
        WHERE comic_id = %s AND chapter_number = %s
    """, (comic_id, chapter_number))
    result = cursor.fetchone()
    return result[0] if result else None

def get_comic_id_from_db(cursor, comic_name):
    cursor.execute("""
        SELECT comic_id 
        FROM comic 
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

def upload_pages_to_db(conn, comic_id, chapter_id, chapter_folder, files):
    """Upload pages directly to the page database"""
    try:
        cursor = conn.cursor()
        
        print(f"Processing Chapter ID {chapter_id} ({len(files)} pages)")
        
        # Sort files numerically (to handle 01.jpg, 02.jpg, etc. correctly)
        files.sort(key=lambda x: int(re.search(r'(\d+)', x).group(1)))
        
        # Insert each page
        for page_number, filename in enumerate(files, 1):
            file_path = os.path.join('Chapters', str(comic_id), chapter_folder, filename)
            
            # Read the image file
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Check if page already exists
            cursor.execute("""
                SELECT page_id 
                FROM page 
                WHERE comic_id = %s AND chapter_id = %s AND page_number = %s
            """, (comic_id, chapter_id, page_number))
            
            if cursor.fetchone():
                # Update existing page
                cursor.execute("""
                    UPDATE page 
                    SET page_image = %s 
                    WHERE comic_id = %s AND chapter_id = %s AND page_number = %s
                """, (image_data, comic_id, chapter_id, page_number))
            else:
                # Insert new page
                cursor.execute("""
                    INSERT INTO page (comic_id, chapter_id, page_number, page_image)
                    VALUES (%s, %s, %s, %s)
                """, (comic_id, chapter_id, page_number, image_data))
            
            print(f"  Uploaded page {page_number}/{len(files)}")
        
        conn.commit()
        print(f"Successfully uploaded all pages for Chapter ID {chapter_id}")
        return True
        
    except Error as e:
        print(f"Error uploading pages to database: {e}")
        conn.rollback()
        return False

def upload_pages_api(comic_id, chapter_id, chapter_folder, files):
    """Upload pages using the page API"""
    try:
        print(f"Processing Chapter ID {chapter_id} ({len(files)} pages)")
        
        # Sort files numerically (to handle 01.jpg, 02.jpg, etc. correctly)
        files.sort(key=lambda x: int(re.search(r'(\d+)', x).group(1)))
        
        # Upload each page
        for page_number, filename in enumerate(files, 1):
            file_path = os.path.join('Chapters', str(comic_id), chapter_folder, filename)
            
            # Prepare the file for upload
            with open(file_path, 'rb') as file:
                files_to_upload = {'page_image': (filename, file, 'image/jpeg')}
                
                # Upload the page
                response = requests.post(
                    f"{PAGE_API_BASE}/upload",
                    data={
                        'comic_id': comic_id,
                        'chapter_id': chapter_id,
                        'page_number': page_number
                    },
                    files=files_to_upload
                )
                
                if response.status_code != 200:
                    print(f"Failed to upload page {page_number}: {response.status_code}")
                    print(response.text)
                    return False
                
            print(f"  Uploaded page {page_number}/{len(files)}")
        
        print(f"Successfully uploaded all pages for Chapter ID {chapter_id}")
        return True
        
    except Exception as e:
        print(f"Error uploading pages via API: {e}")
        return False

def process_chapter(comic_name, chapter_folder, files, use_api=True):
    """Process a single chapter for uploading"""
    # Get comic and chapter information
    comic_conn = get_db_connection(comic_db_config)
    chapter_conn = get_db_connection(chapter_db_config)
    
    if not comic_conn or not chapter_conn:
        return False
    
    try:
        comic_cursor = comic_conn.cursor()
        chapter_cursor = chapter_conn.cursor()
        
        # Get comic_id
        comic_id = get_comic_id_from_db(comic_cursor, comic_name)
        if not comic_id:
            print(f"Comic not found: {comic_name}")
            return False
        
        # Get chapter number from folder name
        chapter_number = extract_chapter_number(chapter_folder)
        if not chapter_number:
            print(f"Could not extract chapter number from: {chapter_folder}")
            return False
        
        # Get chapter_id
        chapter_id = get_chapter_id_from_db(chapter_cursor, comic_id, chapter_number)
        if not chapter_id:
            print(f"Chapter not found: {comic_name} Chapter {chapter_number}")
            return False
        
        if use_api:
            # Upload pages via API
            result = upload_pages_api(comic_id, chapter_id, chapter_folder, files)
        else:
            # Upload pages directly to database
            page_conn = get_db_connection(page_db_config)
            if not page_conn:
                return False
            
            result = upload_pages_to_db(page_conn, comic_id, chapter_id, chapter_folder, files)
            page_conn.close()
            
        return result
        
    except Exception as e:
        print(f"Error processing chapter: {e}")
        return False
    
    finally:
        if comic_conn:
            comic_conn.close()
        if chapter_conn:
            chapter_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Upload comic chapter pages to the page service')
    parser.add_argument('--direct-db', action='store_true', 
                        help='Upload directly to database instead of using the API')
    parser.add_argument('--comic', type=str, help='Process only this comic (by name)')
    parser.add_argument('--chapter', type=str, help='Process only this chapter (by folder name)')
    
    args = parser.parse_args()
    use_api = not args.direct_db
    
    print(f"Using {'direct database connection' if args.direct_db else 'API'} for uploads")
    
    chapters_dir = 'Chapters'
    
    try:
        # Iterate through each comic folder
        for comic_name in os.listdir(chapters_dir):
            # Skip if a specific comic was requested and this isn't it
            if args.comic and args.comic != comic_name:
                continue
                
            comic_path = os.path.join(chapters_dir, comic_name)
            if not os.path.isdir(comic_path):
                continue
            
            print(f"Processing comic: {comic_name}")
            
            # Iterate through each chapter folder
            for chapter_folder in os.listdir(comic_path):
                # Skip if a specific chapter was requested and this isn't it
                if args.chapter and args.chapter != chapter_folder:
                    continue
                    
                chapter_path = os.path.join(comic_path, chapter_folder)
                if not os.path.isdir(chapter_path):
                    continue
                
                print(f"Processing chapter folder: {chapter_folder}")
                
                # Get all image files in the chapter folder
                files = [f for f in os.listdir(chapter_path) 
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                
                if files:
                    process_chapter(comic_name, chapter_folder, files, use_api)
    
    except Exception as e:
        print(f"Error processing folders: {e}")

if __name__ == "__main__":
    main() 