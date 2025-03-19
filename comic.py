from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from enum import Enum
from flask_cors import CORS
import base64
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root', 
    'password': '',
    'database': 'comic_db'
}

# Simple CORS configuration
CORS(app, origins=["http://localhost", "http://localhost:80", "http://127.0.0.1", "http://127.0.0.1:80"])

# Function to connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        print("Database connection successful")
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# Debug route to check if server is running
@app.route('/debug')
def debug():
    return jsonify({
        "status": "running",
        "routes": [str(rule) for rule in app.url_map.iter_rules()]
    })

# Route for home page
@app.route('/')
def home():
    print("Home route accessed")
    return "Welcome to the Comic API!"

# Upload comic image
@app.route('/comic/<int:comic_id>/image', methods=['POST'])
def upload_comic_image(comic_id):
    print(f"Uploading image for comic {comic_id}")
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        try:
            # Read the image file
            image_data = file.read()
            
            # Update the database with the image
            conn = get_db_connection()
            if conn is None:
                return jsonify({"error": "Failed to connect to database"}), 500
            
            cursor = conn.cursor()
            update_query = "UPDATE comic SET comic_art = %s WHERE comic_id = %s"
            cursor.execute(update_query, (image_data, comic_id))
            
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return jsonify({"error": "Comic not found"}), 404
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({"message": "Image uploaded successfully"})
            
        except Exception as e:
            print(f"Error uploading image: {e}")
            return jsonify({"error": str(e)}), 500

# Get comic image
@app.route('/comic/<int:comic_id>/image', methods=['GET'])
def get_comic_image(comic_id):
    print(f"Getting image for comic {comic_id}")
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT comic_art FROM comic WHERE comic_id = %s", (comic_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            cursor.close()
            conn.close()
            return jsonify({"error": "Image not found"}), 404
        
        # Convert BLOB to base64
        image_data = base64.b64encode(result[0]).decode('utf-8')
        
        cursor.close()
        conn.close()
        
        return jsonify({"image": image_data})
        
    except Exception as e:
        print(f"Error getting image: {e}")
        return jsonify({"error": str(e)}), 500

# Get all comics
@app.route('/comic', methods=['GET'])
def get_comics():
    print("GET /comic route accessed")
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to database")
        return jsonify({"error": "Failed to connect to database"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comic")
        comics = cursor.fetchall()
        print(f"Found {len(comics)} comics")
        
        # Convert the tuple data into a dictionary with appropriate keys
        comics_list = []
        for comic in comics:
            # Convert binary image data to base64 if it exists
            comic_art = None
            if comic[6]:  # If comic_art exists
                comic_art = base64.b64encode(comic[6]).decode('utf-8')
            
            comics_list.append({
                "comic_id": comic[0],
                "comic_name": comic[1],
                "author": comic[2],
                "genre": comic[3].split(',') if comic[3] else [],  # Convert comma-separated string to list
                "status": comic[4],
                "description": comic[5],
                "comic_art": comic_art
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(comics_list)
    except Exception as e:
        print(f"Error in get_comics: {e}")
        return jsonify({"error": str(e)}), 500

# Get a specific comic based on its ID
@app.route('/comic/<int:comic_id>', methods=['GET'])
def get_comic(comic_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comic WHERE comic_id = %s", (comic_id,))
    comic = cursor.fetchone()
    
    if comic is None:
        return jsonify({"error": "Comic not found"}), 404
    
    # Convert the tuple data into a dictionary with appropriate keys
    comic_data = {
        "comic_id": comic[0],
        "comic_name": comic[1],
        "author": comic[2],
        "genre": comic[3].split(',') if comic[3] else [],  # Convert comma-separated string to list
        "status": comic[4],
        "description": comic[5],
        "comic_art": comic[6]
    }
    
    cursor.close()
    conn.close()
    
    return jsonify(comic_data)

# Create a new comic
@app.route('/comic', methods=['POST'])
def create_comic():
    comic_data = request.get_json()
    
    # Validate required fields
    required_fields = ['comic_name', 'author', 'genre', 'status', 'description']
    for field in required_fields:
        if field not in comic_data:
            return jsonify({"error": f"{field} is required"}), 400
    
    # Validate status
    valid_statuses = ['ongoing', 'completed', 'hiatus']
    if comic_data['status'] not in valid_statuses:
        return jsonify({"error": "Status must be one of: ongoing, completed, hiatus"}), 400
    
    # Convert genre list to comma-separated string
    genre_str = ','.join(comic_data['genre'])
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO comic (comic_name, author, genre, status, description, comic_art)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        cursor.execute(insert_query, (
            comic_data['comic_name'],
            comic_data['author'],
            genre_str,
            comic_data['status'],
            comic_data['description'],
            comic_data.get('comic_art', None)  # Optional field
        ))
        conn.commit()
        new_comic_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Comic created successfully",
            "comic_id": new_comic_id
        }), 201
        
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to create comic: {err}"}), 500

# Update a comic
@app.route('/comic/<int:comic_id>', methods=['PUT'])
def update_comic(comic_id):
    comic_data = request.get_json()
    
    if not comic_data:
        return jsonify({"error": "No data provided"}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    
    # Build update query dynamically based on provided fields
    update_fields = []
    update_values = []
    
    if 'comic_name' in comic_data:
        update_fields.append("comic_name = %s")
        update_values.append(comic_data['comic_name'])
    
    if 'author' in comic_data:
        update_fields.append("author = %s")
        update_values.append(comic_data['author'])
    
    if 'genre' in comic_data:
        update_fields.append("genre = %s")
        update_values.append(','.join(comic_data['genre']))
    
    if 'status' in comic_data:
        valid_statuses = ['ongoing', 'completed', 'hiatus']
        if comic_data['status'] not in valid_statuses:
            cursor.close()
            conn.close()
            return jsonify({"error": "Status must be one of: ongoing, completed, hiatus"}), 400
        update_fields.append("status = %s")
        update_values.append(comic_data['status'])
    
    if 'description' in comic_data:
        update_fields.append("description = %s")
        update_values.append(comic_data['description'])
    
    if 'comic_art' in comic_data:
        update_fields.append("comic_art = %s")
        update_values.append(comic_data['comic_art'])
    
    if not update_fields:
        cursor.close()
        conn.close()
        return jsonify({"error": "No valid fields to update"}), 400
    
    update_query = f"""
        UPDATE comic
        SET {', '.join(update_fields)}
        WHERE comic_id = %s
    """
    update_values.append(comic_id)
    
    try:
        cursor.execute(update_query, tuple(update_values))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Comic not found"}), 404
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Comic updated successfully"})
        
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to update comic: {err}"}), 500

# Delete a comic
@app.route('/comic/<int:comic_id>', methods=['DELETE'])
def delete_comic(comic_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM comic WHERE comic_id = %s", (comic_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Comic not found"}), 404
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Comic deleted successfully"})
        
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to delete comic: {err}"}), 500

if __name__ == '__main__':
    print("Starting Comic API server...")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"- {rule}")
    app.run(host='0.0.0.0', port=5001, debug=True)
