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
VERIFY_SERVICE_URL2 = "http://localhost:5015/verify/comic/{}/user/{}"

# Configuration
UNLOCK_COST = 100  # Points required to unlock a chapter

@app.route('/api/read_comic/<int:comic_id>/user/<int:user_id>', methods=['GET'])
def read_comic(comic_id, user_id):
    """
    Calls verify history service to fetch comic chapters and their locked status.
    """
    try:
        # Check if refresh parameter is present
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Call verify_chapter_access via VERIFY_SERVICE_URL
        verify_url = VERIFY_SERVICE_URL2.format(comic_id, user_id)
        if refresh:
            verify_url += "?refresh=true"
        
        print(f"Calling verification service with URL: {verify_url}")
        verify_response = requests.get(verify_url)
        
        if not verify_response.ok:
            return jsonify({
                "error": "Failed to fetch verification data",
                "status": verify_response.status_code,
                "message": verify_response.text
            }), 500

        # Return data as-is from verify service (already sorted)
        return verify_response.json()

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Service communication error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route('/purchase/<int:chapter_id>/user/<int:user_id>', methods=['POST'])
def purchase_chapter_access(chapter_id, user_id):
    """
    Process a purchase to unlock a chapter:
    1. Verifies user has enough points (using cached data if available)
    2. Deducts points from user account
    3. Updates reading history
    4. Returns redirect URL
    """
    try:
        # Get user data from request body if available (client-side cached data)
        request_data = request.get_json() or {}
        cached_user_data = request_data.get('user_data')
        
        
        # Only fetch user data if not provided in the request
        if cached_user_data:
            user_data = cached_user_data
            user_points = user_data.get("points", 0)
            print(f"Using cached user data for purchase. User ID: {user_id}, Points: {user_points}")
        else:
            # Fallback: Get current user data from user service
            print(f"No cached user data provided, fetching from user service for ID: {user_id}")
            user_response = requests.get(f"{USER_SERVICE_URL}/{user_id}")
            
            if not user_response.ok:
                return jsonify({
                    "error": "Failed to fetch user data",
                    "status": user_response.status_code,
                    "message": user_response.text
                }), 500
                
            user_data = user_response.json()
            user_points = user_data.get("points", 0)
        
        # Check if user has enough points
        if user_points < UNLOCK_COST:
            return jsonify({
                "status": "insufficient_funds",
                "message": f"Not enough points. Required: {UNLOCK_COST}, Available: {user_points}",
                "subscription_url": "subscription.html"  # URL to subscription page
            }), 402  # 402 Payment Required
        
        # Get chapter details for the redirect URL
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
        
        # Deduct points from user account
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
        
        # Add chapter to reading history to mark it as accessible
        history_response = requests.post(
            f"{HISTORY_SERVICE_URL}",
            json={"user_id": user_id, "chapter_id": chapter_id}
        )
        
        if not history_response.ok:
            # Log warning but continue (consider a compensation transaction here in a real system)
            print(f"Warning: Failed to update history after purchase. User {user_id}, Chapter {chapter_id}")
        
        # Return success with redirect URL - add purchased=true parameter
        return jsonify({
            "status": "success",
            "message": f"Successfully purchased chapter access for {UNLOCK_COST} points",
            "redirect_url": f"{CHAPTER_READER_URL}?chapter_id={chapter_id}&chapter_number={chapter_number}&title={urllib.parse.quote(chapter_title)}&comic_id={comic_id}&refresh=true",
            "points_remaining": points_remaining,
            "chapter_number": chapter_number,
            "title": chapter_title,
            "comic_id": comic_id
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
