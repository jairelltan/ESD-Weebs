import os
import mysql.connector
from mysql.connector import Error
import re

# Database configuration for Docker environment
chapter_db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'chapter_db'
}

# Database configuration for page database
page_db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'page_db'
}

# Database configuration for comic database
comic_db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'comic_db'
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

def get_comic_db_connection():
    try:
        conn = mysql.connector.connect(**comic_db_config)
        print("Comic database connection successful")
        return conn
    except Error as e:
        print(f"Error connecting to comic database: {e}")
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
        FROM comic 
        WHERE comic_name = %s
    """, (comic_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_all_comics(cursor):
    cursor.execute("""
        SELECT comic_id, comic_name 
        FROM comic
    """)
    return cursor.fetchall()

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

def upload_comic_cover(comic_conn, comic_id, comic_name, image_path):
    try:
        cursor = comic_conn.cursor()
        
        # Check if the image file exists
        if not os.path.exists(image_path):
            print(f"Cover image file not found: {image_path}")
            return False
        
        # Read the image file
        with open(image_path, 'rb') as file:
            image_data = file.read()
            
        # Update the comic with the cover image
        cursor.execute("""
            UPDATE comic 
            SET comic_art = %s 
            WHERE comic_id = %s
        """, (image_data, comic_id))
        
        comic_conn.commit()
        print(f"Successfully uploaded cover image for {comic_name}")
        return True
        
    except Error as e:
        print(f"Error uploading cover image: {e}")
        comic_conn.rollback()
        return False

def upload_pages(chapter_conn, page_conn, comic_conn, comic_name, chapter_folder, files):
    try:
        chapter_cursor = chapter_conn.cursor()
        page_cursor = page_conn.cursor()
        comic_cursor = comic_conn.cursor()
        
        # Get comic_id from comic database, not chapter database
        comic_id = get_comic_id(comic_cursor, comic_name)
        if not comic_id:
            print(f"Comic not found: {comic_name}")
            return
        
        # Get chapter number from folder name
        chapter_number = extract_chapter_number(chapter_folder)
        if not chapter_number:
            print(f"Could not extract chapter number from: {chapter_folder}")
            return
        
        # Get chapter_id using the chapter database connection
        chapter_id = get_chapter_id(chapter_cursor, comic_id, chapter_number)
        if not chapter_id:
            print(f"Chapter not found: {comic_name} Chapter {chapter_number}")
            return
        
        print(f"Processing {comic_name} Chapter {chapter_number} ({len(files)} pages)")
        
        # Sort files numerically (to handle 01.jpg, 02.jpg, etc. correctly)
        files.sort(key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0)
        
        # Insert each page
        for page_number, filename in enumerate(files, 1):
            file_path = os.path.join('Chapters', comic_name, chapter_folder, filename)
            
            try:
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
            except FileNotFoundError:
                print(f"  File not found: {file_path}")
                continue
            except Error as e:
                print(f"  Error processing page {page_number}: {e}")
                continue
        
        page_conn.commit()
        print(f"Successfully uploaded all pages for {comic_name} Chapter {chapter_number}")
        
    except Error as e:
        print(f"Error uploading pages: {e}")
        page_conn.rollback()

def process_cover_images(comic_conn):
    """Process all cover images from the images folder and update comics"""
    
    try:
        cursor = comic_conn.cursor()
        comics = get_all_comics(cursor)
        
        images_dir = 'images'
        if not os.path.exists(images_dir):
            print(f"Error: {images_dir} directory not found")
            return
            
        image_files = os.listdir(images_dir)
        
        # Track which comics had covers updated
        updated_comics = []
        
        for comic_id, comic_name in comics:
            # Try different possible filename patterns for cover images
            possible_filenames = [
                f"{comic_name.lower().replace(' ', '_')}.jpg",
                f"{comic_name.lower().replace(' ', '_')}.webp",
                f"{comic_name.lower().replace(' ', '_')}.png",
                f"{comic_name.lower()}.jpg",
                f"{comic_name.lower()}.webp",
                f"{comic_name.lower()}.png"
            ]
            
            # Check if any of the possible filenames exist
            for filename in possible_filenames:
                if filename in image_files:
                    image_path = os.path.join(images_dir, filename)
                    success = upload_comic_cover(comic_conn, comic_id, comic_name, image_path)
                    if success:
                        updated_comics.append(comic_name)
                        break
            
        # Print summary
        if updated_comics:
            print(f"\nUpdated cover images for {len(updated_comics)} comics:")
            for comic in updated_comics:
                print(f"- {comic}")
        else:
            print("\nNo cover images were updated")
                
    except Error as e:
        print(f"Error processing cover images: {e}")

def main():
    chapter_conn = get_chapter_db_connection()
    page_conn = get_page_db_connection()
    comic_conn = get_comic_db_connection()
    
    if not chapter_conn or not page_conn or not comic_conn:
        print("Failed to connect to one or more databases. Exiting.")
        return
    
    print("\n=== PROCESSING COMIC COVER IMAGES ===")
    process_cover_images(comic_conn)
    
    print("\n=== PROCESSING CHAPTER PAGES ===")
    chapters_dir = 'Chapters'
    if not os.path.exists(chapters_dir):
        print(f"Error: {chapters_dir} directory not found")
        return
    
    # Process chapters
    for comic_folder in os.listdir(chapters_dir):
        comic_path = os.path.join(chapters_dir, comic_folder)
        if os.path.isdir(comic_path):
            for chapter_folder in os.listdir(comic_path):
                chapter_path = os.path.join(comic_path, chapter_folder)
                if os.path.isdir(chapter_path):
                    # Get all image files in this chapter folder
                    files = [f for f in os.listdir(chapter_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))]
                    if files:
                        upload_pages(chapter_conn, page_conn, comic_conn, comic_folder, chapter_folder, files)
    
    # Close connections
    if chapter_conn:
        chapter_conn.close()
    if page_conn:
        page_conn.close()
    if comic_conn:
        comic_conn.close()

if __name__ == "__main__":
    main() 