from flask import Flask, request, jsonify, redirect, url_for
import requests
from flask_cors import CORS
import time
from datetime import datetime
import urllib.parse

app = Flask(__name__)
CORS(app)

# Define service URLs
VERIFY_SERVICE_URL = "http://localhost:5015/verify/chapter"
HISTORY_SERVICE_URL = "http://localhost:5014/api/history"
USER_SERVICE_URL = "http://localhost:5000/user"
CHAPTER_READER_URL = "chapter-reader.html"

# Configuration
UNLOCK_COST = 100  # Points required to unlock a chapter

@app.route('/api/read_comic/<int:comic_id>/user/<int:user_id>', methods=['GET'])
def read_comic(comic_id, user_id):
    """
    Composite service to fetch comic chapters and determine their locked status.
    """
    try:
        # Fetch all chapters for the comic
        chapters_response = requests.get(f"http://localhost:5005/api/comics/{comic_id}/chapters")
        if not chapters_response.ok:
            return jsonify({
                "error": "Failed to fetch comic chapters",
                "status": chapters_response.status_code,
                "message": chapters_response.text
            }), 500
        
        chapters_data = chapters_response.json()
        
        # Fetch user's reading history
        history_response = requests.get(f"http://localhost:5014/api/history/user/{user_id}")
        if not history_response.ok:
            return jsonify({
                "error": "Failed to fetch user reading history",
                "status": history_response.status_code,
                "message": history_response.text
            }), 500
        
        history_data = history_response.json()
        
        # Create a set of read chapter IDs
        read_chapter_ids = set()
        if history_data.get("history"):
            for entry in history_data["history"]:
                if "chapter_id" in entry:
                    read_chapter_ids.add(entry["chapter_id"])

        # Process chapters to determine locked status
        processed_chapters = [
            {
                **chapter,
                "is_locked": chapter["chapter_id"] not in read_chapter_ids
            }
            for chapter in chapters_data["chapters"]
        ]

        # Sort chapters in descending order
        processed_chapters.sort(key=lambda c: float(c["chapter_number"]), reverse=True)

        return jsonify({"chapters": processed_chapters})
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Service communication error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route('/purchase/<int:chapter_id>/user/<int:user_id>', methods=['POST'])
def purchase_chapter_access(chapter_id, user_id):
    """
    Process a purchase to unlock a chapter:
    1. Verifies user has enough points
    2. Deducts points from user account
    3. Updates reading history
    4. Returns redirect URL
    """
    try:
        # 1. Get current user data
        user_response = requests.get(f"{USER_SERVICE_URL}/{user_id}")
        
        if not user_response.ok:
            return jsonify({
                "error": "Failed to fetch user data",
                "status": user_response.status_code,
                "message": user_response.text
            }), 500
            
        user_data = user_response.json()
        user_points = user_data.get("points", 0)
        
        # 2. Check if user has enough points
        if user_points < UNLOCK_COST:
            return jsonify({
                "status": "insufficient_funds",
                "message": f"Not enough points. Required: {UNLOCK_COST}, Available: {user_points}",
                "subscription_url": "subscription.html"  # URL to subscription page
            }), 402  # 402 Payment Required
        
        # 2.5 Get chapter details for the redirect URL
        chapter_response = requests.get(f"http://localhost:5005/api/chapters/{chapter_id}")
        if not chapter_response.ok:
            return jsonify({
                "error": "Failed to fetch chapter details", 
                "status": chapter_response.status_code,
                "message": chapter_response.text
            }), 500
            
        chapter_data = chapter_response.json()
        comic_id = chapter_data.get("comic_id", "1")
        chapter_number = chapter_data.get("chapter_number", "1")
        chapter_title = chapter_data.get("title", "")
        
        # 3. Deduct points from user account
        update_response = requests.put(
            f"{USER_SERVICE_URL}/{user_id}/points",
            json={"deduct": UNLOCK_COST}
        )
        
        if not update_response.ok:
            return jsonify({
                "error": "Failed to update user points",
                "status": update_response.status_code,
                "message": update_response.text
            }), 500
        
        # Get the updated points from the response
        update_data = update_response.json()
        points_remaining = update_data.get("points", 0)
        
        # 4. Add chapter to reading history to mark it as accessible
        history_response = requests.post(
            f"{HISTORY_SERVICE_URL}/add",
            json={"user_id": user_id, "chapter_id": chapter_id}
        )
        
        if not history_response.ok:
            # Log warning but continue (consider a compensation transaction here in a real system)
            print(f"Warning: Failed to update history after purchase. User {user_id}, Chapter {chapter_id}")
        
        # 5. Return success with redirect URL - add purchased=true parameter
        return jsonify({
            "status": "success",
            "message": f"Successfully purchased chapter access for {UNLOCK_COST} points",
            "redirect_url": f"{CHAPTER_READER_URL}?chapter_id={chapter_id}&chapter_number={chapter_number}&title={urllib.parse.quote(chapter_title)}&comic_id={comic_id}&purchased=true",
            "points_remaining": points_remaining
        })
            
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Service communication error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service"""
    return jsonify({
        "status": "up",
        "service": "read_comic",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020, debug=True)
