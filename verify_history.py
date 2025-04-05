from flask import Flask, request, jsonify, make_response
import requests
from flask_cors import CORS
import time
from datetime import datetime

app = Flask(__name__)

# Configure CORS to allow requests from any origin with proper settings
CORS(app, resources={r"/*": {
    "origins": "*", 
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    "expose_headers": ["Content-Type", "X-Total-Count", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "supports_credentials": True
}})

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

# Handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

# Define service URLs
CHAPTER_SERVICE_URL = "http://app:5005/api/comics"
HISTORY_SERVICE_URL = "http://app:5014/api/history/user"

# Add specific OPTIONS handlers for verify endpoints
@app.route('/verify/comic/<int:comic_id>/user/<int:user_id>', methods=['OPTIONS'])
def options_verify_comic(comic_id, user_id):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

@app.route('/verify/chapter/<int:chapter_id>/user/<int:user_id>', methods=['OPTIONS'])
def options_verify_chapter(chapter_id, user_id):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

# Simple in-memory cache
cache = {}
CACHE_DURATION = 300  # 5 minutes in seconds

def get_cached_data(key, fetch_func, *args, refresh=False):
    """Get data from cache or fetch it"""
    now = time.time()
    
    # Check if data is in cache and not expired, and no refresh is requested
    if not refresh and key in cache and cache[key]['expiry'] > now:
        return cache[key]['data']
    
    # Fetch new data
    data = fetch_func(*args)
    
    # Store in cache
    cache[key] = {
        'data': data,
        'expiry': now + CACHE_DURATION
    }
    
    return data

def fetch_chapters(comic_id):
    """Fetch chapters for a comic"""
    response = requests.get(f"{CHAPTER_SERVICE_URL}/{comic_id}/chapters")
    if response.status_code == 200:
        return response.json().get("chapters", [])
    return []

def fetch_history(user_id):
    """Fetch user reading history directly (not cached)"""
    response = requests.get(f"{HISTORY_SERVICE_URL}/{user_id}")
    if response.status_code == 200:
        return response.json().get("history", [])
    return []

@app.route('/verify/comic/<int:comic_id>/user/<int:user_id>', methods=['GET'])
def verify_chapter_access(comic_id, user_id):
    """
    Composite microservice that:
    1. Fetches all chapters for a comic
    2. Checks which chapters the user has read in history
    3. Marks chapters as locked/unlocked based on reading history
    """
    try:
        start_time = time.time()
        
        # Check if refresh is requested
        refresh_history = request.args.get('refresh', 'false').lower() == 'true'
        
        # 1. Fetch all chapters for the comic
        chapters = get_cached_data(f"chapters_{comic_id}", fetch_chapters, comic_id)
        if not chapters:
            return jsonify({"message": "No chapters found for this comic", "chapters": []})
        
        # 2. Get user's reading history - with optional refresh
        user_history = get_cached_data(f"history_{user_id}", fetch_history, user_id, refresh=refresh_history)
        
        # 3. Extract chapter IDs from history (use a set for O(1) lookups)
        read_chapter_ids = {entry["chapter_id"] for entry in user_history if "chapter_id" in entry}
        
        # 4. Process chapters to add locked status (using list comprehension for better performance)
        processed_chapters = [
            {
                "chapter_id": chapter.get("chapter_id"),
                "chapter_number": chapter.get("chapter_number"),
                "title": chapter.get("title"),
                "release_date": chapter.get("release_date"),
                "is_locked": chapter.get("chapter_id") not in read_chapter_ids
            }
            for chapter in chapters
        ]
        
        # 5. Sort chapters by chapter number in descending order
        processed_chapters.sort(key=lambda c: float(c["chapter_number"]), reverse=True)
        
        # Record performance metric only for slow operations
        elapsed_time = time.time() - start_time
        if elapsed_time > 0.5:  # Only log slow operations (>500ms)
            print(f"SLOW: Processed {len(processed_chapters)} chapters in {elapsed_time:.3f}s")
        
        return jsonify({
            "comic_id": comic_id,
            "user_id": user_id,
            "chapters": processed_chapters
        })
            
    except requests.exceptions.RequestException as e:
        print(f"Service communication error: {str(e)}")
        return jsonify({"error": f"Service communication error: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/verify/chapter/<int:chapter_id>/user/<int:user_id>', methods=['GET'])
def verify_single_chapter_access(chapter_id, user_id):
    """
    Verify if a user has access to a specific chapter by checking if it's in their reading history
    """
    try:
        start_time = time.time()
        
        # Check if refresh is requested
        refresh_history = request.args.get('refresh', 'false').lower() == 'true'
        
        # 1. Get user's reading history - with optional refresh
        user_history = get_cached_data(f"history_{user_id}", fetch_history, user_id, refresh=refresh_history)
        
        # 2. Extract chapter IDs from history (use a set for O(1) lookups)
        read_chapter_ids = {entry["chapter_id"] for entry in user_history if "chapter_id" in entry}
        
        # 3. Check if this specific chapter has been read
        is_accessible = chapter_id in read_chapter_ids
        
        # Record performance metric only for slow operations
        elapsed_time = time.time() - start_time
        if elapsed_time > 0.2:  # Only log slow operations (>200ms)
            print(f"SLOW: Verification completed in {elapsed_time:.3f}s - Chapter {chapter_id}")
        
        return jsonify({
            "chapter_id": chapter_id,
            "user_id": user_id,
            "is_accessible": is_accessible,
            "reason": "in_history" if is_accessible else "not_in_history"
        })
            
    except Exception as e:
        print(f"Error in verify_single_chapter_access: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}", "is_accessible": False}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service"""
    return jsonify({
        "status": "up",
        "service": "verify_history",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "cache_keys": list(cache.keys())
    })

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Admin endpoint to clear the cache"""
    cache_size = len(cache)
    cache_keys = list(cache.keys())
    cache.clear()
    print(f"Cache cleared. Removed {cache_size} items: {cache_keys}")
    return jsonify({
        "message": "Cache cleared successfully", 
        "cleared_items": cache_size,
        "keys": cache_keys
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5015, debug=True)
