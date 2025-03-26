from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import mysql.connector
import os
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'Chapters'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'page_db'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to database: {e}")
        return None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    result = {
        "status": "ok" if conn else "error",
        "service": "page-service",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if conn else "error"
    }
    
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            result["tables"] = tables
        except mysql.connector.Error as e:
            result["error"] = str(e)
        finally:
            cursor.close()
            conn.close()
    
    return jsonify(result)

@app.route('/api/pages/chapter/<int:chapter_id>', methods=['GET'])
def get_chapter_pages(chapter_id):
    """Get all page numbers for a chapter"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all page numbers for this chapter
        cursor.execute("""
            SELECT page_number, comic_id 
            FROM page 
            WHERE chapter_id = %s 
            ORDER BY page_number
        """, (chapter_id,))
        
        pages_data = cursor.fetchall()
        
        if not pages_data:
            return jsonify({"error": f"No pages found for chapter ID {chapter_id}"}), 404
        
        # Extract page numbers and get comic_id (should be the same for all pages)
        pages = [page['page_number'] for page in pages_data]
        comic_id = pages_data[0]['comic_id'] if pages_data else None
        
        return jsonify({
            "chapter_id": chapter_id,
            "comic_id": comic_id,
            "pages": pages
        })
    
    except mysql.connector.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/pages/chapter/<int:chapter_id>/page/<int:page_number>', methods=['GET'])
def get_page_image(chapter_id, page_number):
    """Get a specific page image"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT page_image 
            FROM page 
            WHERE chapter_id = %s AND page_number = %s
        """, (chapter_id, page_number))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": f"Page {page_number} not found for chapter {chapter_id}"}), 404
        
        # Send the image as a response
        image_data = result[0]
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'chapter_{chapter_id}_page_{page_number}.jpg'
        )
    
    except mysql.connector.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/pages/upload', methods=['POST'])
def upload_page():
    """Upload a page image"""
    if 'page_image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['page_image']
    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400
    
    # Get form data
    comic_id = request.form.get('comic_id')
    chapter_id = request.form.get('chapter_id')
    page_number = request.form.get('page_number')
    
    if not all([comic_id, chapter_id, page_number]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        comic_id = int(comic_id)
        chapter_id = int(chapter_id)
        page_number = int(page_number)
    except ValueError:
        return jsonify({"error": "Invalid parameter values"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        # Read the image data
        image_data = file.read()
        
        # Check if the page already exists
        cursor.execute("""
            SELECT 1 FROM page 
            WHERE chapter_id = %s AND page_number = %s
        """, (chapter_id, page_number))
        
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update the existing page
            cursor.execute("""
                UPDATE page 
                SET page_image = %s, comic_id = %s
                WHERE chapter_id = %s AND page_number = %s
            """, (image_data, comic_id, chapter_id, page_number))
            message = "Page updated successfully"
        else:
            # Insert a new page
            cursor.execute("""
                INSERT INTO page (chapter_id, page_number, comic_id, page_image) 
                VALUES (%s, %s, %s, %s)
            """, (chapter_id, page_number, comic_id, image_data))
            message = "Page uploaded successfully"
        
        conn.commit()
        
        return jsonify({
            "message": message,
            "chapter_id": chapter_id,
            "page_number": page_number
        })
    
    except mysql.connector.Error as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    
    finally:
        cursor.close()
        conn.close()

# @app.route('/api/pages/chapter/<int:chapter_id>/delete', methods=['DELETE'])
# def delete_chapter_pages(chapter_id):
#     """Delete all pages for a chapter"""
#     conn = get_db_connection()
#     if not conn:
#         return jsonify({"error": "Database connection failed"}), 500
    
#     cursor = conn.cursor()
#     try:
#         # Check if pages exist for this chapter
#         cursor.execute("SELECT COUNT(*) FROM page WHERE chapter_id = %s", (chapter_id,))
#         count = cursor.fetchone()[0]
        
#         if count == 0:
#             return jsonify({"error": f"No pages found for chapter {chapter_id}"}), 404
        
#         # Delete all pages for this chapter
#         cursor.execute("DELETE FROM page WHERE chapter_id = %s", (chapter_id,))
#         conn.commit()
        
#         return jsonify({
#             "message": f"Successfully deleted {count} pages for chapter {chapter_id}"
#         })
    
#     except mysql.connector.Error as e:
#         conn.rollback()
#         return jsonify({"error": f"Database error: {str(e)}"}), 500
    
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/api/pages/chapter/<int:chapter_id>/page/<int:page_number>', methods=['DELETE'])
# def delete_page(chapter_id, page_number):
#     """Delete a specific page"""
#     conn = get_db_connection()
#     if not conn:
#         return jsonify({"error": "Database connection failed"}), 500
    
#     cursor = conn.cursor()
#     try:
#         # Check if the page exists
#         cursor.execute("""
#             SELECT 1 FROM page 
#             WHERE chapter_id = %s AND page_number = %s
#         """, (chapter_id, page_number))
        
#         if not cursor.fetchone():
#             return jsonify({"error": f"Page {page_number} not found for chapter {chapter_id}"}), 404
        
#         # Delete the page
#         cursor.execute("""
#             DELETE FROM page 
#             WHERE chapter_id = %s AND page_number = %s
#         """, (chapter_id, page_number))
        
#         conn.commit()
        
#         return jsonify({
#             "message": f"Successfully deleted page {page_number} for chapter {chapter_id}"
#         })
    
#     except mysql.connector.Error as e:
#         conn.rollback()
#         return jsonify({"error": f"Database error: {str(e)}"}), 500
    
#     finally:
#         cursor.close()
#         conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013, debug=True) 