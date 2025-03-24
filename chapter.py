from flask import Flask, request, jsonify, Response, send_file
import mysql.connector
from mysql.connector import Error
import io
import base64
from flask_cors import CORS
import os
import traceback
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Database configuration
chapter_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'chapter_db'
}

comic_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'comic_db'
}

# Configure upload folder
UPLOAD_FOLDER = 'Chapters'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_chapter_db_connection():
    try:
        conn = mysql.connector.connect(**chapter_db_config)
        print("Chapter database connection successful")
        return conn
    except Error as e:
        print(f"Error connecting to chapter database: {e}")
        return None

def get_comic_db_connection():
    try:
        conn = mysql.connector.connect(**comic_db_config)
        print("Comic database connection successful")
        return conn
    except Error as e:
        print(f"Error connecting to comic database: {e}")
        return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "running",
        "message": "Chapter API is running",
        "endpoints": [
            "/api/comics/<comic_id>/chapters",
            "/api/chapters/<chapter_id>",
            "/api/chapters/<chapter_id>/pages",
            "/api/chapters/<chapter_id>/pages/<page_number>",
            "/api/chapters/<chapter_id>/navigation",
            "/api/chapter/<chapter_id>/upload"
        ]
    })

@app.route('/api/test-db', methods=['GET'])
def test_db():
    chapter_conn = get_chapter_db_connection()
    comic_conn = get_comic_db_connection()
    
    result = {
        "chapter_db": "connected" if chapter_conn else "error",
        "comic_db": "connected" if comic_conn else "error"
    }
    
    if chapter_conn:
        try:
            cursor = chapter_conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            result["chapter_tables"] = tables
        except Error as e:
            result["chapter_error"] = str(e)
        finally:
            cursor.close()
            chapter_conn.close()
    
    if comic_conn:
        try:
            cursor = comic_conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            result["comic_tables"] = tables
        except Error as e:
            result["comic_error"] = str(e)
        finally:
            cursor.close()
            comic_conn.close()
    
    return jsonify(result)

# Route to get all chapters for a comic
@app.route('/api/comics/<int:comic_id>/chapters', methods=['GET'])
def get_chapters(comic_id):
    print(f"Get chapters request for comic ID: {comic_id}")
    
    # First check if comic exists
    comic_conn = get_comic_db_connection()
    if not comic_conn:
        return jsonify({"error": "Comic database connection failed"}), 500
    
    chapter_conn = None
    
    try:
        comic_cursor = comic_conn.cursor(dictionary=True)
        
        # Get the comic name
        comic_cursor.execute("""
            SELECT comic_id, comic_name 
            FROM comic 
            WHERE comic_id = %s
        """, (comic_id,))
        
        comic = comic_cursor.fetchone()
        print(f"Comic query result: {comic}")
        
        if not comic:
            return jsonify({"error": "Comic not found"}), 404
        
        # Now get chapters from chapter database
        chapter_conn = get_chapter_db_connection()
        if not chapter_conn:
            return jsonify({"error": "Chapter database connection failed"}), 500
        
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        
        # Get all chapters for this comic
        query = """
            SELECT chapter_id, chapter_number, title, release_date
            FROM chapter
            WHERE comic_id = %s
            ORDER BY chapter_number
        """
        print(f"Executing chapter query: {query} with comic_id={comic_id}")
        
        chapter_cursor.execute(query, (comic_id,))
        chapters = chapter_cursor.fetchall()
        print(f"Found {len(chapters)} chapters")
        
        # Convert date to string to make it JSON serializable
        for chapter in chapters:
            if 'release_date' in chapter and chapter['release_date']:
                chapter['release_date'] = chapter['release_date'].isoformat()
        
        result = {
            "comic_id": comic_id,
            "comic_name": comic["comic_name"],
            "chapters": chapters
        }
        
        return jsonify(result)
    
    except Error as e:
        print(f"Database error in get_chapters: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in get_chapters: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if comic_conn and hasattr(comic_conn, 'is_connected') and comic_conn.is_connected():
            comic_cursor.close()
            comic_conn.close()
        if chapter_conn and hasattr(chapter_conn, 'is_connected') and chapter_conn.is_connected():
            chapter_cursor.close()
            chapter_conn.close()

# Route to get a specific chapter's details
@app.route('/api/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(chapter_id):
    print(f"Get chapter request for chapter ID: {chapter_id}")
    
    chapter_conn = get_chapter_db_connection()
    if not chapter_conn:
        return jsonify({"error": "Chapter database connection failed"}), 500
    
    comic_conn = get_comic_db_connection()
    if not comic_conn:
        if chapter_conn:
            chapter_conn.close()
        return jsonify({"error": "Comic database connection failed"}), 500
    
    try:
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        comic_cursor = comic_conn.cursor(dictionary=True)
        
        # Get chapter details
        chapter_cursor.execute("""
            SELECT chapter_id, comic_id, chapter_number, title, release_date
            FROM chapter
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        chapter = chapter_cursor.fetchone()
        print(f"Chapter query result: {chapter}")
        
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404
        
        # Get comic name
        comic_cursor.execute("""
            SELECT comic_name 
            FROM comic 
            WHERE comic_id = %s
        """, (chapter["comic_id"],))
        
        comic = comic_cursor.fetchone()
        print(f"Comic query result: {comic}")
        
        # Get page count
        chapter_cursor.execute("""
            SELECT COUNT(page_id) as page_count
            FROM chapter_pages
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        page_count = chapter_cursor.fetchone()
        print(f"Page count query result: {page_count}")
        
        # Build complete chapter object
        complete_chapter = {
            **chapter,
            "comic_name": comic["comic_name"] if comic else "Unknown",
            "page_count": page_count["page_count"] if page_count else 0
        }
        
        # Convert date to string
        if 'release_date' in complete_chapter and complete_chapter['release_date']:
            complete_chapter['release_date'] = complete_chapter['release_date'].isoformat()
        
        return jsonify(complete_chapter)
    
    except Error as e:
        print(f"Database error in get_chapter: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in get_chapter: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if chapter_conn and hasattr(chapter_conn, 'is_connected') and chapter_conn.is_connected():
            chapter_cursor.close()
            chapter_conn.close()
        if comic_conn and hasattr(comic_conn, 'is_connected') and comic_conn.is_connected():
            comic_cursor.close()
            comic_conn.close()

# Route to get a specific page image from a chapter
@app.route('/api/chapters/<int:chapter_id>/pages/<int:page_number>', methods=['GET'])
def get_page_image(chapter_id, page_number):
    print(f"Get page image request for chapter ID: {chapter_id}, page: {page_number}")
    
    conn = get_chapter_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get the page image data
        cursor.execute("""
            SELECT page_image
            FROM chapter_pages
            WHERE chapter_id = %s AND page_number = %s
        """, (chapter_id, page_number))
        
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "Page not found"}), 404
        
        image_data = result[0]
        
        # Return the image as a response
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg'  # Assuming the image is JPEG - adjust if needed
        )
    
    except Error as e:
        print(f"Database error in get_page_image: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in get_page_image: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if conn and hasattr(conn, 'is_connected') and conn.is_connected():
            cursor.close()
            conn.close()

# Route to get all page numbers for a chapter
@app.route('/api/chapters/<int:chapter_id>/pages', methods=['GET'])
def get_chapter_pages(chapter_id):
    print(f"Get chapter pages request for chapter ID: {chapter_id}")
    
    chapter_conn = get_chapter_db_connection()
    if not chapter_conn:
        return jsonify({"error": "Chapter database connection failed"}), 500
    
    comic_conn = get_comic_db_connection()
    if not comic_conn:
        if chapter_conn:
            chapter_conn.close()
        return jsonify({"error": "Comic database connection failed"}), 500
    
    try:
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        comic_cursor = comic_conn.cursor(dictionary=True)
        
        # First check if the chapter exists
        chapter_cursor.execute("""
            SELECT chapter_id, comic_id, chapter_number, title
            FROM chapter
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        chapter = chapter_cursor.fetchone()
        print(f"Chapter query result: {chapter}")
        
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404
        
        # Get comic name
        comic_cursor.execute("""
            SELECT comic_name 
            FROM comic 
            WHERE comic_id = %s
        """, (chapter["comic_id"],))
        
        comic = comic_cursor.fetchone()
        print(f"Comic query result: {comic}")
        
        # Get all page numbers for this chapter
        chapter_cursor.execute("""
            SELECT page_number
            FROM chapter_pages
            WHERE chapter_id = %s
            ORDER BY page_number
        """, (chapter_id,))
        
        pages = [row["page_number"] for row in chapter_cursor.fetchall()]
        print(f"Found {len(pages)} pages")
        
        result = {
            "chapter_id": chapter_id,
            "comic_id": chapter["comic_id"],
            "comic_name": comic["comic_name"] if comic else "Unknown",
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "pages": pages,
            "page_count": len(pages)
        }
        
        return jsonify(result)
    
    except Error as e:
        print(f"Database error in get_chapter_pages: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in get_chapter_pages: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if chapter_conn and hasattr(chapter_conn, 'is_connected') and chapter_conn.is_connected():
            chapter_cursor.close()
            chapter_conn.close()
        if comic_conn and hasattr(comic_conn, 'is_connected') and comic_conn.is_connected():
            comic_cursor.close()
            comic_conn.close()

# Route to get the previous and next chapter IDs for navigation
@app.route('/api/chapters/<int:chapter_id>/navigation', methods=['GET'])
def get_chapter_navigation(chapter_id):
    print(f"Get chapter navigation request for chapter ID: {chapter_id}")
    
    conn = get_chapter_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get current chapter details
        cursor.execute("""
            SELECT chapter_id, comic_id, chapter_number
            FROM chapter
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        current = cursor.fetchone()
        print(f"Current chapter query result: {current}")
        
        if not current:
            return jsonify({"error": "Chapter not found"}), 404
        
        comic_id = current["comic_id"]
        chapter_number = current["chapter_number"]
        
        # Get previous chapter
        cursor.execute("""
            SELECT chapter_id, chapter_number
            FROM chapter
            WHERE comic_id = %s AND chapter_number < %s
            ORDER BY chapter_number DESC
            LIMIT 1
        """, (comic_id, chapter_number))
        
        prev_chapter = cursor.fetchone()
        print(f"Previous chapter query result: {prev_chapter}")
        
        # Get next chapter
        cursor.execute("""
            SELECT chapter_id, chapter_number
            FROM chapter
            WHERE comic_id = %s AND chapter_number > %s
            ORDER BY chapter_number ASC
            LIMIT 1
        """, (comic_id, chapter_number))
        
        next_chapter = cursor.fetchone()
        print(f"Next chapter query result: {next_chapter}")
        
        result = {
            "current_chapter_id": chapter_id,
            "current_chapter_number": chapter_number,
            "comic_id": comic_id,
            "previous_chapter": prev_chapter or None,
            "next_chapter": next_chapter or None
        }
        
        return jsonify(result)
    
    except Error as e:
        print(f"Database error in get_chapter_navigation: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in get_chapter_navigation: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if conn and hasattr(conn, 'is_connected') and conn.is_connected():
            cursor.close()
            conn.close()

# Upload chapter images
@app.route('/api/chapter/<int:chapter_id>/upload', methods=['POST'])
def upload_chapter_images(chapter_id):
    print(f"Upload chapter images request for chapter ID: {chapter_id}")
    
    if 'images' not in request.files:
        return jsonify({"error": "No images provided"}), 400
    
    chapter_conn = get_chapter_db_connection()
    if not chapter_conn:
        return jsonify({"error": "Chapter database connection failed"}), 500
    
    comic_conn = get_comic_db_connection()
    if not comic_conn:
        if chapter_conn:
            chapter_conn.close()
        return jsonify({"error": "Comic database connection failed"}), 500
    
    try:
        # First, get the chapter info to create proper directory structure
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        comic_cursor = comic_conn.cursor(dictionary=True)
        
        chapter_cursor.execute("""
            SELECT chapter_id, comic_id, chapter_number
            FROM chapter
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        chapter = chapter_cursor.fetchone()
        print(f"Chapter query result: {chapter}")
        
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404
        
        comic_cursor.execute("""
            SELECT comic_name
            FROM comic
            WHERE comic_id = %s
        """, (chapter["comic_id"],))
        
        comic = comic_cursor.fetchone()
        print(f"Comic query result: {comic}")
        
        if not comic:
            return jsonify({"error": "Comic not found"}), 404
        
        # Create directory structure if it doesn't exist
        comic_dir = os.path.join(app.config['UPLOAD_FOLDER'], comic['comic_name'])
        chapter_dir = os.path.join(comic_dir, f"Chapter {chapter['chapter_number']}")
        os.makedirs(chapter_dir, exist_ok=True)
        
        uploaded_files = []
        files = request.files.getlist('images')
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(chapter_dir, filename)
                file.save(file_path)
                uploaded_files.append(filename)
        
        if not uploaded_files:
            return jsonify({"error": "No valid images uploaded"}), 400
        
        # Update the chapter's image path in the database
        image_path = os.path.join(comic['comic_name'], f"Chapter {chapter['chapter_number']}")
        chapter_cursor.execute("""
            UPDATE chapter 
            SET image = %s 
            WHERE chapter_id = %s
        """, (image_path, chapter_id))
        chapter_conn.commit()
        
        return jsonify({
            "message": "Images uploaded successfully",
            "uploaded_files": uploaded_files,
            "chapter_path": image_path
        })
    
    except Error as e:
        print(f"Database error in upload_chapter_images: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in upload_chapter_images: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        if chapter_conn and hasattr(chapter_conn, 'is_connected') and chapter_conn.is_connected():
            chapter_cursor.close()
            chapter_conn.close()
        if comic_conn and hasattr(comic_conn, 'is_connected') and comic_conn.is_connected():
            comic_cursor.close()
            comic_conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True) 