from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Define service URLs
CHAPTER_SERVICE_URL = "http://localhost:5005/api/comics"
HISTORY_SERVICE_URL = "http://localhost:5014/api/history/user"
USER_SERVICE_URL = "http://localhost:5000/user"

# Simple in-memory cache
cache = {}
CACHE_DURATION = 300  # 5 minutes in seconds

def get_cached_data(key, fetch_func, *args):
    """Get data from cache or fetch it"""
    now = time.time()
    
    # Check if data is in cache and not expired
    if key in cache and cache[key]['expiry'] > now:
        return cache[key]['data']
    
    # Fetch new data
    data = fetch_func(*args)
    
    # Store in cache
    cache[key] = {
        'data': data,
        'expiry': now + CACHE_DURATION
    }
    
    return data

def fetch_user(user_id):
    """Fetch user data"""
    response = requests.get(f"{USER_SERVICE_URL}/{user_id}")
    if response.status_code == 200:
        return response.json()
    return None

def fetch_chapters(comic_id):
    """Fetch chapters for a comic"""
    response = requests.get(f"{CHAPTER_SERVICE_URL}/{comic_id}/chapters")
    if response.status_code == 200:
        return response.json().get("chapters", [])
    return []

def fetch_history(user_id):
    """Fetch user reading history"""
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
        
        # 1. Verify the user exists
        user = get_cached_data(f"user_{user_id}", fetch_user, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # 2. Fetch all chapters for the comic
        chapters = get_cached_data(f"chapters_{comic_id}", fetch_chapters, comic_id)
        if not chapters:
            return jsonify({"message": "No chapters found for this comic", "chapters": []})
        
        # 3. Get user's reading history
        user_history = get_cached_data(f"history_{user_id}", fetch_history, user_id)
        
        # Extract chapter IDs from history
        read_chapter_ids = set()
        for entry in user_history:
            if "chapter_id" in entry:
                read_chapter_ids.add(entry["chapter_id"])
        
        # Process chapters to add locked status
        processed_chapters = []
        for chapter in chapters:
            chapter_id = chapter.get("chapter_id")
            
            # A chapter is unlocked if it's in the reading history
            is_unlocked = chapter_id in read_chapter_ids
            
            chapter_data = {
                "chapter_id": chapter_id,
                "chapter_number": chapter.get("chapter_number"),
                "title": chapter.get("title"),
                "release_date": chapter.get("release_date"),
                "is_locked": not is_unlocked
            }
            processed_chapters.append(chapter_data)
        
        # Record performance metric
        elapsed_time = time.time() - start_time
        print(f"Processed {len(processed_chapters)} chapters in {elapsed_time:.3f}s")
        
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
        
        # 1. Verify the user exists
        user = get_cached_data(f"user_{user_id}", fetch_user, user_id)
        if not user:
            return jsonify({"error": "User not found", "is_accessible": False}), 404
        
        # 2. Get user's reading history
        user_history = get_cached_data(f"history_{user_id}", fetch_history, user_id)
        
        # Extract chapter IDs from history
        read_chapter_ids = set()
        for entry in user_history:
            if "chapter_id" in entry:
                read_chapter_ids.add(entry["chapter_id"])
        
        # Check if this specific chapter has been read
        is_accessible = chapter_id in read_chapter_ids
        
        # Record performance metric
        elapsed_time = time.time() - start_time
        print(f"Verification completed in {elapsed_time:.3f}s - Chapter {chapter_id} is {'accessible' if is_accessible else 'not accessible'}")
        
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
        "cache_size": len(cache)
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
