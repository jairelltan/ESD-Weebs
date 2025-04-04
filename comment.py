from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'comments_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None

# Get comments for a thread
@app.route('/comments/thread/<int:thread_id>', methods=['GET'])
def get_thread_comments(thread_id):
    try:
        logger.info(f"Fetching comments for thread {thread_id}")
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM comments 
            WHERE thread_id = %s 
            ORDER BY created_at DESC
        """, (thread_id,))
        
        comments = cursor.fetchall()
        logger.info(f"Found {len(comments)} comments for thread {thread_id}")
        
        cursor.close()
        conn.close()
        
        return jsonify(comments)
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Get replies for a comment
@app.route('/comments/<int:comment_id>/replies', methods=['GET'])
def get_comment_replies(comment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM comments
            WHERE parent_id = %s
            ORDER BY created_at ASC
        """
        cursor.execute(query, (comment_id,))
        replies = cursor.fetchall()
        
        return jsonify(replies)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Create a new comment
@app.route('/comment', methods=['POST'])
def create_comment():
    try:
        data = request.json
        logger.info(f"Creating comment with data: {data}")
        
        # Validate required fields
        required_fields = ['thread_id', 'user_id', 'content']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor()
        
        # Insert the comment
        cursor.execute("""
            INSERT INTO comments (thread_id, user_id, content, created_at)
            VALUES (%s, %s, %s, %s)
        """, (
            data['thread_id'],
            data['user_id'],
            data['content'],
            datetime.now()
        ))
        
        conn.commit()
        comment_id = cursor.lastrowid
        logger.info(f"Created comment with ID: {comment_id}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Comment created successfully",
            "comment_id": comment_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Like a comment
@app.route('/comment/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    try:
        logger.info(f"Liking comment {comment_id}")
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comments 
            SET likes = likes + 1 
            WHERE comment_id = %s
        """, (comment_id,))
        
        conn.commit()
        logger.info(f"Successfully liked comment {comment_id}")
        
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Comment liked successfully"})
        
    except Exception as e:
        logger.error(f"Error liking comment: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5012, debug=True) 
