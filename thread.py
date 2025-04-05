from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from enum import Enum
from flask_cors import CORS

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'thread_db'  # Separate database for threads
}

CORS(app)

# Enum for Thread Status
class ThreadStatus(Enum):
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"

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
        print(f"Database connection error: {err}")
        return None

# Route for home page
@app.route('/')
def home():
    return "Welcome to the Thread Microservice!"

# Get all threads
@app.route('/threads', methods=['GET'])
def get_all_threads():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM threads ORDER BY create_date DESC")
    threads = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(threads)

# Get threads by chapter
@app.route('/threads/chapter/<int:chapter_id>', methods=['GET'])
def get_threads_by_chapter(chapter_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM threads WHERE chapter_id = %s ORDER BY create_date DESC", (chapter_id,))
    threads = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(threads)

# Get comment count for a thread
@app.route('/thread/<int:thread_id>/comments/count', methods=['GET'])
def get_thread_comment_count(thread_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT comment_count 
        FROM threads 
        WHERE thread_id = %s
    """, (thread_id,))
    
    result = cursor.fetchone()
    count = result['comment_count'] if result else 0
    
    cursor.close()
    conn.close()
    
    return jsonify({"count": count})

# Update thread comment count
@app.route('/thread/<int:thread_id>/comments/count', methods=['PUT'])
def update_thread_comment_count(thread_id):
    try:
        # Get the new count from the request
        data = request.get_json()
        if not data or 'count' not in data:
            return jsonify({"error": "Count not provided"}), 400
            
        new_count = data['count']
        
        # Update the count in the thread database
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Update thread's comment count
        cursor.execute("""
            UPDATE threads 
            SET comment_count = %s 
            WHERE thread_id = %s
        """, (new_count, thread_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"count": new_count})
        
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

# Create a new thread
@app.route('/thread', methods=['POST'])
def create_thread():
    # Get thread data from request
    thread_data = request.get_json()

    # Validate input
    required_fields = ['chapter_id', 'user_id', 'title', 'content']
    for field in required_fields:
        if field not in thread_data:
            return jsonify({"error": f"{field} is required"}), 400

    # Connect to database
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()

    # Prepare insert query
    insert_query = """
    INSERT INTO threads 
    (chapter_id, user_id, title, content, create_date, status, likes, comment_count) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Prepare values
    create_date = datetime.now()
    status = ThreadStatus.PUBLISHED.value
    likes = 0
    comment_count = 0

    # Execute the query
    try:
        cursor.execute(insert_query, (
            thread_data['chapter_id'], 
            thread_data['user_id'], 
            thread_data['title'], 
            thread_data['content'], 
            create_date, 
            status, 
            likes, 
            comment_count
        ))

        # Commit the changes
        conn.commit()

        # Get the ID of the newly created thread
        new_thread_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Thread created successfully", 
            "thread_id": new_thread_id
        }), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

# Update thread status
@app.route('/thread/<int:thread_id>/status', methods=['PUT'])
def update_thread_status(thread_id):
    # Get the data from the request
    thread_data = request.get_json()

    # Validate if status is provided
    if not thread_data or "status" not in thread_data:
        return jsonify({"error": "Status not provided"}), 400

    status = thread_data["status"]

    # Validate if status is valid
    valid_statuses = [status.value for status in ThreadStatus]
    if status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of {valid_statuses}"}), 400
    
    # Connect to the database
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()

    # SQL query to update the status of the thread
    update_query = """
    UPDATE threads
    SET status = %s
    WHERE thread_id = %s
    """

    # Execute the query
    cursor.execute(update_query, (status, thread_id))

    # Commit the changes
    conn.commit()

    # Check if any row was updated
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({"error": "Thread not found"}), 404

    cursor.close()
    conn.close()

    return jsonify({"message": "Thread status updated successfully"})

# Like a thread
@app.route('/thread/<int:thread_id>/like', methods=['POST'])
def like_thread(thread_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    
    # Update thread's like count
    cursor.execute("""
        UPDATE threads 
        SET likes = likes + 1 
        WHERE thread_id = %s
    """, (thread_id,))
    
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Thread liked successfully"})

if __name__ == '__main__':
    app.run(port=5011, debug=True)

