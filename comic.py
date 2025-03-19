from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from enum import Enum
from flask_cors import CORS

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
        return conn
    except mysql.connector.Error as err:
        print(f"Something went wrong: {err}")
        return None

# Route for home page
@app.route('/')
def home():
    return "Welcome to the Comic API!"

# Get all comics
@app.route('/comic', methods=['GET'])
def get_comics():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comic")
    comics = cursor.fetchall()
    
    # Convert the tuple data into a dictionary with appropriate keys
    comics_list = []
    for comic in comics:
        comics_list.append({
            "comic_id": comic[0],
            "comic_name": comic[1],
            "author": comic[2],
            "genre": comic[3].split(',') if comic[3] else [],  # Convert comma-separated string to list
            "status": comic[4],
            "description": comic[5],
            "comic_art": comic[6]
        })
    
    cursor.close()
    conn.close()
    
    return jsonify(comics_list)

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
    app.run(port=5001, debug=True)
