from flask import Flask, request, jsonify, redirect, url_for, send_file
import requests
from flask_cors import CORS
import time
from datetime import datetime
import urllib.parse
import io
import base64

app = Flask(__name__)
CORS(app)

# Define service URLs
VERIFY_SERVICE_URL = "http://localhost:5015/verify/chapter"
HISTORY_SERVICE_URL = "http://localhost:5014/api/history"
USER_SERVICE_URL = "http://localhost:5000/user"
CHAPTER_READER_URL = "chapter-reader.html"
VERIFY_SERVICE_URL2 = "http://localhost:5015/verify/comic/{}/user/{}"
PAGE_SERVICE_URL = "http://localhost:5013/api/pages"

# Configuration
UNLOCK_COST = 100  # Points required to unlock a chapter

# Simple in-memory cache for the most critical resources
PAGE_CACHE = {}  # Simple dictionary for most frequent pages

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


@app.route('/api/chapter/<int:chapter_id>/pages', methods=['GET'])
def get_chapter_pages(chapter_id):
    """
    Composite endpoint that fetches chapter page information.
    Optionally includes the first page image data for faster initial loading.
    """
    try:
        # Get include_first parameter with default false
        include_first = request.args.get('include_first', 'false').lower() == 'true'
        
        # Call the page service to get page numbers
        response = requests.get(f"{PAGE_SERVICE_URL}/chapter/{chapter_id}")
        
        if not response.ok:
            return jsonify({
                "error": "Failed to fetch page data",
                "status": response.status_code,
                "message": response.text
            }), response.status_code
        
        # Get the basic page data
        page_data = response.json()
        
        # If requested, include the first page image inline
        if include_first and page_data.get("pages") and len(page_data["pages"]) > 0:
            try:
                first_page_num = page_data["pages"][0]
                
                # Check for cached first page
                cache_key = f"{chapter_id}_{first_page_num}"
                if cache_key in PAGE_CACHE:
                    # Use cached image
                    first_page_image = PAGE_CACHE[cache_key]
                else:
                    # Fetch the first page image
                    img_response = requests.get(f"{PAGE_SERVICE_URL}/chapter/{chapter_id}/page/{first_page_num}")
                    
                    if img_response.ok and img_response.content:
                        first_page_image = img_response.content
                        # Cache the first page for future requests
                        PAGE_CACHE[cache_key] = first_page_image
                    else:
                        first_page_image = None
                
                if first_page_image:
                    # Add the first page image as base64
                    page_data["first_page_image"] = base64.b64encode(first_page_image).decode('utf-8')
                    page_data["first_page_number"] = first_page_num
            except Exception as img_error:
                # Log but don't fail if first page fetch fails
                print(f"Error fetching first page: {str(img_error)}")
        
        # Add URLs for each page to make client-side loading easier
        if page_data.get("pages"):
            page_data["page_urls"] = {
                page_num: f"/api/chapter/{chapter_id}/page/{page_num}" 
                for page_num in page_data["pages"]
            }
        
        return jsonify(page_data)
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Service communication error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route('/api/chapter/<int:chapter_id>/page/<int:page_number>', methods=['GET'])
def get_page_image(chapter_id, page_number):
    """
    Composite endpoint that fetches a specific page image from the page service.
    Adding caching headers for better performance.
    """
    try:
        # Check for cached page
        cache_key = f"{chapter_id}_{page_number}"
        if cache_key in PAGE_CACHE:
            # Use cached image
            image_data = PAGE_CACHE[cache_key]
        else:
            # Call the page service to get the image
            response = requests.get(f"{PAGE_SERVICE_URL}/chapter/{chapter_id}/page/{page_number}", stream=True)
            
            if not response.ok:
                return jsonify({
                    "error": f"Failed to fetch page {page_number}",
                    "status": response.status_code
                }), response.status_code
            
            # Get image data
            image_data = response.content
            
            # Cache only smaller images (less than 1MB) to avoid memory issues
            if len(image_data) < 1000000:
                PAGE_CACHE[cache_key] = image_data
        
        # Send file with basic cache headers
        response = send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'chapter_{chapter_id}_page_{page_number}.jpg'
        )
        
        # Add simple cache headers - cache for 1 day
        response.headers['Cache-Control'] = 'public, max-age=86400'
        
        return response
        
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
        
        # Return success with redirect URL - add refresh=true parameter
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
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(PAGE_CACHE)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020, debug=True)
