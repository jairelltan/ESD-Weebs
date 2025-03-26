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

@app.route('/read/<int:chapter_id>/user/<int:user_id>', methods=['GET'])
def process_chapter_access(chapter_id, user_id):
    """
    Composite microservice that:
    1. Checks if a chapter is accessible using verify_history
    2. If unlocked, redirects to chapter and updates history
    3. If locked, returns data to prompt payment
    """
    try:
        # 1. Check if chapter is already accessible
        verify_response = requests.get(f"{VERIFY_SERVICE_URL}/{chapter_id}/user/{user_id}")
        
        if not verify_response.ok:
            return jsonify({
                "error": "Failed to verify chapter access",
                "status": verify_response.status_code,
                "message": verify_response.text
            }), 500
            
        verify_data = verify_response.json()
        
        # 1.5 Get chapter details for the redirect URL
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
        
        # 2. If chapter is already accessible, update history and redirect
        if verify_data.get("is_accessible", False):
            # Update read history (do this in background without waiting for response)
            try:
                requests.post(
                    f"{HISTORY_SERVICE_URL}/add", 
                    json={"user_id": user_id, "chapter_id": chapter_id},
                    timeout=1  # Short timeout since we don't need to wait
                )
            except requests.exceptions.RequestException:
                # Log but continue even if history update fails
                print(f"Warning: Failed to update history for user {user_id}, chapter {chapter_id}")
                
            # Return success with redirect URL
            return jsonify({
                "status": "success",
                "message": "Chapter is accessible",
                "redirect_url": f"{CHAPTER_READER_URL}?chapter_id={chapter_id}&chapter_number={chapter_number}&title={urllib.parse.quote(chapter_title)}&comic_id={comic_id}",
                "is_accessible": True
            })
        
        # 3. If chapter is locked, check user balance
        user_response = requests.get(f"{USER_SERVICE_URL}/{user_id}")
        
        if not user_response.ok:
            return jsonify({
                "error": "Failed to fetch user data",
                "status": user_response.status_code,
                "message": user_response.text,
                "is_accessible": False
            }), 500
            
        user_data = user_response.json()
        user_points = user_data.get("points", 0)
        
        # 4. Return purchase information
        return jsonify({
            "status": "locked",
            "message": "Chapter requires payment to unlock",
            "is_accessible": False,
            "chapter_id": chapter_id,
            "chapter_number": chapter_number,
            "comic_id": comic_id,
            "title": chapter_title,
            "unlock_cost": UNLOCK_COST,
            "user_points": user_points,
            "can_afford": user_points >= UNLOCK_COST
        })
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"Service communication error: {str(e)}",
            "is_accessible": False
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}",
            "is_accessible": False
        }), 500

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
        
        # 5. Return success with redirect URL
        return jsonify({
            "status": "success",
            "message": f"Successfully purchased chapter access for {UNLOCK_COST} points",
            "redirect_url": f"{CHAPTER_READER_URL}?chapter_id={chapter_id}&chapter_number={chapter_number}&title={urllib.parse.quote(chapter_title)}&comic_id={comic_id}",
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
