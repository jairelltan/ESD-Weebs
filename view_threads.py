from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import mysql.connector
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
THREAD_SERVICE_URL = "http://localhost:5011"
COMMENT_SERVICE_URL = "http://localhost:5012"
CHAPTER_SERVICE_URL = "http://localhost:5005"
USER_SERVICE_URL = "http://localhost:5000"

# Database configuration for caching
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'composite_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None

def setup_database():
    """Setup the database and required tables"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Create thread_comment_counts table for caching
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS thread_comment_counts (
                    thread_id INT PRIMARY KEY,
                    comment_count INT DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Database setup completed successfully")
        except mysql.connector.Error as err:
            logger.error(f"Error setting up database: {err}")
        finally:
            cursor.close()
            conn.close()

def update_thread_comment_count(thread_id):
    """Update the cached comment count for a thread"""
    try:
        # Get comment count from comment service
        logger.info(f"Fetching comments for thread {thread_id}")
        response = requests.get(f"{COMMENT_SERVICE_URL}/comments/thread/{thread_id}")
        
        if response.ok:
            comments = response.json()
            count = len(comments)
            logger.info(f"Found {count} comments for thread {thread_id}")
            
            # Update the count in thread service
            logger.info(f"Updating thread {thread_id} comment count to {count}")
            thread_response = requests.put(
                f"{THREAD_SERVICE_URL}/thread/{thread_id}/comments/count",
                json={"count": count}
            )
            
            if thread_response.ok:
                # Update cache
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO thread_comment_counts (thread_id, comment_count)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE
                        comment_count = VALUES(comment_count)
                    """, (thread_id, count))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"Successfully updated cache for thread {thread_id}")
                    return count
            else:
                logger.error(f"Failed to update thread service: {thread_response.text}")
        else:
            logger.error(f"Failed to fetch comments: {response.text}")
    except Exception as e:
        logger.error(f"Error updating comment count: {str(e)}")
    return None

def get_thread_comment_count(thread_id):
    """Get the cached comment count for a thread"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT comment_count, last_updated
                FROM thread_comment_counts
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            
            # If no cache or cache is old (more than 5 minutes), update it
            if not result or (datetime.now() - result['last_updated']).total_seconds() > 300:
                logger.info(f"Cache miss or expired for thread {thread_id}, updating...")
                count = update_thread_comment_count(thread_id)
                if count is not None:
                    return count
            
            return result['comment_count'] if result else 0
        finally:
            cursor.close()
            conn.close()
    return 0

@app.route('/api/threads/chapter/<int:chapter_id>', methods=['GET'])
def get_chapter_threads(chapter_id):
    """Get all threads for a chapter with complete information"""
    try:
        # Get threads from thread service
        logger.info(f"Fetching threads for chapter {chapter_id}")
        thread_response = requests.get(f"{THREAD_SERVICE_URL}/threads/chapter/{chapter_id}")
        if not thread_response.ok:
            logger.error(f"Failed to fetch threads: {thread_response.text}")
            return jsonify({"error": "Failed to fetch threads"}), 500
        
        threads = thread_response.json()
        
        # Get chapter details
        chapter_response = requests.get(f"{CHAPTER_SERVICE_URL}/api/chapters/{chapter_id}")
        chapter_data = chapter_response.json() if chapter_response.ok else None
        
        # Enrich thread data
        enriched_threads = []
        for thread in threads:
            # Get comment count
            comment_count = get_thread_comment_count(thread['thread_id'])
            
            # Get user details
            user_response = requests.get(f"{USER_SERVICE_URL}/user/{thread['user_id']}")
            user_data = user_response.json() if user_response.ok else None
            
            # Combine all data
            enriched_thread = {
                **thread,
                'comment_count': comment_count,
                'chapter': chapter_data,
                'user': user_data
            }
            enriched_threads.append(enriched_thread)
        
        return jsonify(enriched_threads)
    
    except Exception as e:
        logger.error(f"Error in get_chapter_threads: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/thread/<int:thread_id>', methods=['GET'])
def get_thread_details(thread_id):
    """Get detailed information about a specific thread"""
    try:
        # Get thread details
        thread_response = requests.get(f"{THREAD_SERVICE_URL}/thread/{thread_id}")
        if not thread_response.ok:
            return jsonify({"error": "Thread not found"}), 404
        
        thread = thread_response.json()
        
        # Get comments
        comment_response = requests.get(f"{COMMENT_SERVICE_URL}/comments/thread/{thread_id}")
        comments = comment_response.json() if comment_response.ok else []
        
        # Get user details
        user_response = requests.get(f"{USER_SERVICE_URL}/user/{thread['user_id']}")
        user_data = user_response.json() if user_response.ok else None
        
        # Get chapter details
        chapter_response = requests.get(f"{CHAPTER_SERVICE_URL}/api/chapters/{thread['chapter_id']}")
        chapter_data = chapter_response.json() if chapter_response.ok else None
        
        # Combine all data
        enriched_thread = {
            **thread,
            'comments': comments,
            'user': user_data,
            'chapter': chapter_data
        }
        
        return jsonify(enriched_thread)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/thread/<int:thread_id>/comments', methods=['GET'])
def get_thread_comments(thread_id):
    """Get all comments for a thread"""
    try:
        logger.info(f"Fetching comments for thread {thread_id}")
        # Get comments from comment service
        response = requests.get(f"{COMMENT_SERVICE_URL}/comments/thread/{thread_id}")
        if not response.ok:
            logger.error(f"Failed to fetch comments: {response.text}")
            return jsonify({"error": "Failed to fetch comments"}), 500
        
        comments = response.json()
        
        # Get user details for each comment
        enriched_comments = []
        for comment in comments:
            user_response = requests.get(f"{USER_SERVICE_URL}/user/{comment['user_id']}")
            user_data = user_response.json() if user_response.ok else None
            
            enriched_comment = {
                **comment,
                'user': user_data
            }
            enriched_comments.append(enriched_comment)
        
        return jsonify(enriched_comments)
    
    except Exception as e:
        logger.error(f"Error in get_thread_comments: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/thread/<int:thread_id>/comment', methods=['POST'])
def create_thread_comment(thread_id):
    """Create a new comment for a thread"""
    try:
        data = request.json
        data['thread_id'] = thread_id
        
        logger.info(f"Creating comment for thread {thread_id}")
        # Create comment
        response = requests.post(f"{COMMENT_SERVICE_URL}/comment", json=data)
        if not response.ok:
            logger.error(f"Failed to create comment: {response.text}")
            return jsonify({"error": "Failed to create comment"}), 500
        
        # Update comment count
        logger.info(f"Updating comment count for thread {thread_id}")
        update_thread_comment_count(thread_id)
        
        return response.json()
    
    except Exception as e:
        logger.error(f"Error in create_thread_comment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "view-threads",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    setup_database()
    app.run(port=5025, debug=True) 