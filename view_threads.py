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
        else:
            logger.error(f"Failed to fetch comments: {response.text}")
    except Exception as e:
        logger.error(f"Error updating comment count: {str(e)}")
    return None

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
    app.run(port=5025, debug=True) 