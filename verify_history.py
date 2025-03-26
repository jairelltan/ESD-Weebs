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
    3. Adds lock symbol to unread chapters based on reading order
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
        
        # Sort chapters by number (because we need to check previous chapters)
        sorted_chapters = sorted(chapters, key=lambda x: float(x.get("chapter_number", 0)))
        
        # Process chapters to add locked status
        processed_chapters = []
        for i, chapter in enumerate(sorted_chapters):
            chapter_id = chapter.get("chapter_id")
            chapter_number = float(chapter.get("chapter_number", 0))
            
            # A chapter is unlocked if:
            # 1. It's chapter 1 (always accessible)
            # 2. It's in the reading history
            # 3. Previous chapter has been read
            is_unlocked = False
            
            if chapter_number == 1:
                # First chapter is always accessible
                is_unlocked = True
            elif chapter_id in read_chapter_ids:
                # This chapter has been read
                is_unlocked = True
            elif i > 0:
                # Check if previous chapter has been read
                prev_chapter_id = sorted_chapters[i-1].get("chapter_id")
                if prev_chapter_id in read_chapter_ids:
                    is_unlocked = True
            
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
    Verify if a user has access to a specific chapter by checking:
    1. If it's the first chapter (always accessible)
    2. If user has read the previous chapter
    3. If user has purchased this chapter
    """
    try:
        start_time = time.time()
        
        # 1. Verify the user exists
        user = get_cached_data(f"user_{user_id}", fetch_user, user_id)
        if not user:
            return jsonify({"error": "User not found", "is_accessible": False}), 404
        
        # 2. Get chapter information to check if it's the first chapter
        # and get the comic_id to find the previous chapter
        chapter_info = None
        try:
            chapter_response = requests.get(f"http://localhost:5005/api/chapters/{chapter_id}")
            if chapter_response.status_code == 200:
                chapter_info = chapter_response.json()
        except Exception as e:
            print(f"Error fetching chapter info: {str(e)}")
            # Continue processing even if chapter info fetch fails
        
        # If it's the first chapter, it's always accessible
        if chapter_info and chapter_info.get("chapter_number") == "1":
            print(f"Chapter {chapter_id} is the first chapter, granting access")
            return jsonify({
                "chapter_id": chapter_id,
                "user_id": user_id,
                "is_accessible": True,
                "reason": "first_chapter"
            })
        
        # 3. Get user's reading history
        user_history = get_cached_data(f"history_{user_id}", fetch_history, user_id)
        
        # Extract chapter IDs from history
        read_chapter_ids = set()
        for entry in user_history:
            if "chapter_id" in entry:
                read_chapter_ids.add(entry["chapter_id"])
        
        # 4. Check if this specific chapter has been read
        if chapter_id in read_chapter_ids:
            print(f"Chapter {chapter_id} already in reading history, granting access")
            return jsonify({
                "chapter_id": chapter_id,
                "user_id": user_id,
                "is_accessible": True,
                "reason": "in_history"
            })
        
        # 5. Check if previous chapter has been read (if this isn't chapter 1)
        if chapter_info and chapter_info.get("chapter_number") != "1":
            comic_id = chapter_info.get("comic_id")
            current_chapter_number = float(chapter_info.get("chapter_number", 0))
            
            # Get all chapters for this comic
            all_chapters = get_cached_data(f"chapters_{comic_id}", fetch_chapters, comic_id)
            
            # Find the previous chapter
            previous_chapter = None
            for chapter in all_chapters:
                chapter_num = float(chapter.get("chapter_number", 0))
                if chapter_num < current_chapter_number and (previous_chapter is None or 
                                                           float(previous_chapter.get("chapter_number", 0)) < chapter_num):
                    previous_chapter = chapter
            
            # If previous chapter exists and has been read, allow access
            if previous_chapter and previous_chapter.get("chapter_id") in read_chapter_ids:
                print(f"Previous chapter {previous_chapter.get('chapter_id')} has been read, granting access")
                return jsonify({
                    "chapter_id": chapter_id,
                    "user_id": user_id,
                    "is_accessible": True,
                    "reason": "previous_chapter_read"
                })
        
        # Record performance metric
        elapsed_time = time.time() - start_time
        print(f"Verification completed in {elapsed_time:.3f}s - Chapter {chapter_id} is not accessible")
        
        return jsonify({
            "chapter_id": chapter_id,
            "user_id": user_id,
            "is_accessible": False,
            "reason": "not_in_sequence"
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
