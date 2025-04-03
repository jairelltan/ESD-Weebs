from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'comments_db'
}

# Thread service URL
THREAD_SERVICE_URL = "http://localhost:5011"

def get_db_connection():
    return mysql.connector.connect(**db_config)

def update_thread_comment_count(thread_id):
    """Update the comment count in the thread service"""
    try:
        # First get the current count of comments for this thread
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comments WHERE thread_id = %s", (thread_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Update the count in the thread service
        response = requests.put(
            f"{THREAD_SERVICE_URL}/thread/{thread_id}/comments/count",
            json={"count": count}
        )
        
        if not response.ok:
            print(f"Failed to update thread comment count: {response.text}")
            
    except Exception as e:
        print(f"Error updating thread comment count: {str(e)}")

# Get comments for a thread
@app.route('/comments/thread/<int:thread_id>', methods=['GET'])
def get_thread_comments(thread_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all comments for the thread, ordered by created_at in ascending order (oldest first)
        query = """
            SELECT c.*, 
                   (SELECT COUNT(*) FROM comments WHERE parent_id = c.comment_id) as reply_count
            FROM comments c
            WHERE c.thread_id = %s AND c.parent_id IS NULL
            ORDER BY c.created_at ASC
        """
        cursor.execute(query, (thread_id,))
        comments = cursor.fetchall()
        
        return jsonify(comments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO comments (thread_id, user_id, parent_id, content)
            VALUES (%s, %s, %s, %s)
        """
        values = (
            data.get('thread_id'),
            data.get('user_id'),
            data.get('parent_id'),
            data.get('content')
        )
        
        cursor.execute(query, values)
        conn.commit()
        
        # Update the thread's comment count
        thread_id = data.get('thread_id')
        if thread_id:
            update_thread_comment_count(thread_id)
        
        return jsonify({
            'message': 'Comment created successfully',
            'comment_id': cursor.lastrowid
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Like a comment
@app.route('/comment/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "UPDATE comments SET likes = likes + 1 WHERE comment_id = %s"
        cursor.execute(query, (comment_id,))
        conn.commit()
        
        return jsonify({'message': 'Comment liked successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(port=5012, debug=True) 
