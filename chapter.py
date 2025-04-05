from flask import Flask, request, jsonify, Response, send_file, make_response
import mysql.connector
from mysql.connector import Error
import io
import base64
from flask_cors import CORS
import os
import traceback
import requests
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {
    "origins": "*", 
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    "expose_headers": ["Content-Type", "X-Total-Count", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "supports_credentials": True
}})

# Database configuration
chapter_db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'chapter_db'
}

# Configure upload folder
UPLOAD_FOLDER = 'Chapters'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# Handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

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

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "running",
        "message": "Chapter API is running",
        "endpoints": [
            "/api/comics/<comic_id>/chapters",
            "/api/chapters/<chapter_id>",
            "/api/chapters/<chapter_id>/pages"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    chapter_conn = get_chapter_db_connection()
    
    result = {
        "chapter_db": "connected" if chapter_conn else "error",
        "service": "chapter-service",
        "status": "ok" if chapter_conn else "error",
        "timestamp": datetime.now().isoformat()
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
    
    return jsonify(result)

# Route to get all chapters for a comic
@app.route('/api/comics/<int:comic_id>/chapters', methods=['GET'])
def get_chapters(comic_id):
    print(f"Get chapters request for comic ID: {comic_id}")
    
    chapter_conn = None
    
    try:
        # Get chapters from chapter database
        chapter_conn = get_chapter_db_connection()
        if not chapter_conn:
            return jsonify({"error": "Chapter database connection failed"}), 500
        
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        
        # Get all chapters for this comic
        query = """
            SELECT chapter_id, chapter_number, title, release_date, comic_id
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
    
    try:
        chapter_cursor = chapter_conn.cursor(dictionary=True)
        
        # Get chapter details
        chapter_cursor.execute("""
            SELECT chapter_id, comic_id, chapter_number, title, release_date 
            FROM chapter 
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        chapter = chapter_cursor.fetchone()
        
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404
        
        # Convert date to string to make it JSON serializable
        if 'release_date' in chapter and chapter['release_date']:
            chapter['release_date'] = chapter['release_date'].isoformat()
        
        return jsonify(chapter)
    
    except Error as e:
        print(f"Database error in get_chapter: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if chapter_conn:
            chapter_cursor.close()
            chapter_conn.close()

# Route to get chapter metadata for navigation
@app.route('/api/chapters/<int:chapter_id>/navigation', methods=['GET'])
def get_chapter_navigation(chapter_id):
    chapter_conn = get_chapter_db_connection()
    if not chapter_conn:
        return jsonify({"error": "Chapter database connection failed"}), 500
    
    try:
        cursor = chapter_conn.cursor(dictionary=True)
        
        # First get the current chapter to find its comic_id and chapter_number
        cursor.execute("""
            SELECT comic_id, chapter_number 
            FROM chapter 
            WHERE chapter_id = %s
        """, (chapter_id,))
        
        current_chapter = cursor.fetchone()
        if not current_chapter:
            return jsonify({"error": "Chapter not found"}), 404
        
        comic_id = current_chapter['comic_id']
        chapter_number = current_chapter['chapter_number']
        
        # Get previous chapter
        cursor.execute("""
            SELECT chapter_id, chapter_number
            FROM chapter
            WHERE comic_id = %s AND chapter_number < %s
            ORDER BY chapter_number DESC
            LIMIT 1
        """, (comic_id, chapter_number))
        
        prev_chapter = cursor.fetchone()
        
        # Get next chapter
        cursor.execute("""
            SELECT chapter_id, chapter_number
            FROM chapter
            WHERE comic_id = %s AND chapter_number > %s
            ORDER BY chapter_number ASC
            LIMIT 1
        """, (comic_id, chapter_number))
        
        next_chapter = cursor.fetchone()
        
        return jsonify({
            "current_chapter_id": chapter_id,
            "comic_id": comic_id,
            "current_chapter_number": chapter_number,
            "prev_chapter": prev_chapter,
            "next_chapter": next_chapter
        })
    
    except Error as e:
        print(f"Database error in get_chapter_navigation: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        cursor.close()
        chapter_conn.close()

# Route to create a new chapter
@app.route('/api/chapters', methods=['POST'])
def create_chapter():
    data = request.get_json()
    
    # Validate required parameters
    required_fields = ['comic_id', 'chapter_number', 'title']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    chapter_conn = get_chapter_db_connection()
    if not chapter_conn:
        return jsonify({"error": "Chapter database connection failed"}), 500
    
    try:
        chapter_cursor = chapter_conn.cursor()
        
        # Check if chapter already exists
        chapter_cursor.execute("""
            SELECT chapter_id FROM chapter 
            WHERE comic_id = %s AND chapter_number = %s
        """, (data['comic_id'], data['chapter_number']))
        
        if chapter_cursor.fetchone():
            return jsonify({"error": "Chapter already exists"}), 409
        
        # Set release date as current time if not provided
        release_date = data.get('release_date', datetime.now().isoformat())
        
        # Create the chapter
        chapter_cursor.execute("""
            INSERT INTO chapter (comic_id, chapter_number, title, release_date)
            VALUES (%s, %s, %s, %s)
        """, (data['comic_id'], data['chapter_number'], data['title'], release_date))
        
        chapter_conn.commit()
        chapter_id = chapter_cursor.lastrowid
        
        return jsonify({
            "message": "Chapter created successfully",
            "chapter_id": chapter_id
        }), 201
    
    except Error as e:
        print(f"Database error in create_chapter: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        chapter_cursor.close()
        chapter_conn.close()

# # Route to delete a chapter
# @app.route('/api/chapters/<int:chapter_id>', methods=['DELETE'])
# def delete_chapter(chapter_id):
#     chapter_conn = get_chapter_db_connection()
#     if not chapter_conn:
#         return jsonify({"error": "Chapter database connection failed"}), 500
    
#     try:
#         chapter_cursor = chapter_conn.cursor()
        
#         # Check if chapter exists
#         chapter_cursor.execute("SELECT chapter_id FROM chapter WHERE chapter_id = %s", (chapter_id,))
#         if not chapter_cursor.fetchone():
#             return jsonify({"error": "Chapter not found"}), 404
        
#         # Delete the chapter
#         chapter_cursor.execute("DELETE FROM chapter WHERE chapter_id = %s", (chapter_id,))
#         chapter_conn.commit()
        
#         return jsonify({"message": "Chapter deleted successfully"})
    
#     except Error as e:
#         print(f"Database error in delete_chapter: {e}")
#         return jsonify({"error": str(e)}), 500
    
#     finally:
#         chapter_cursor.close()
#         chapter_conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True) 