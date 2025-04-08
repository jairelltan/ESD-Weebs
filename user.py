from flask import Flask, request, jsonify, make_response
import mysql.connector
from datetime import datetime
from enum import Enum
from flask_cors import CORS

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root', 
    'password': 'root_password',
    'database': 'user_db'
}

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

# Function to connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Something went wrong: {err}")
        return None

# Route for home page
@app.route('/')
def home():
    return "Welcome to the User API!"

#get all users
@app.route('/user', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    
    # Convert the tuple data into a dictionary with appropriate keys
    users_list = []
    for user in users:
        users_list.append({
            "id": user[0],
            "name": user[1],
            "phone": user[2],
            "email": user[3],
            "address": user[4],
            "points": user[5],
            "status": user[6]
        })
    
    cursor.close()
    conn.close()
    
    return jsonify(users_list)

#get a specific user base on their ID
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    
    # Convert the tuple data into a dictionary with appropriate keys
    user_data = {
        "id": user[0],
        "name": user[1],
        "phone": user[2],
        "email": user[3],
        "address": user[4],
        "points": user[5],
        "status": user[6]
    }
    
    cursor.close()
    conn.close()
    
    return jsonify(user_data)

# API to update points for a user
@app.route('/user/<int:user_id>/points', methods=['PUT'])
def update_points(user_id):
    # Get the data from the request (assumed to be in JSON format)
    user_data = request.get_json()

    # Check if we're directly setting points or deducting/adding
    if not user_data:
        return jsonify({"error": "Request body is required"}), 400

    if "points" in user_data:
        # Direct setting of points
        points = user_data["points"]
        
        # Validate if points is a valid number
        if not isinstance(points, int):
            return jsonify({"error": "Points must be an integer"}), 400
        
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Failed to connect to database"}), 500

        cursor = conn.cursor()

        # SQL query to update the points of the user
        update_query = """
            UPDATE user
            SET points = %s
            WHERE user_id = %s
        """

        # Execute the query
        cursor.execute(update_query, (points, user_id))

    elif "deduct" in user_data or "add" in user_data:
        # Deduct or add points from current balance
        amount = user_data.get("deduct", 0) if "deduct" in user_data else -user_data.get("add", 0)
        
        # Validate if amount is a valid number
        if not isinstance(amount, int):
            return jsonify({"error": "Amount must be an integer"}), 400
        
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Failed to connect to database"}), 500

        cursor = conn.cursor()

        # First, check if the user exists and get current points
        cursor.execute("SELECT points FROM user WHERE user_id = %s", (user_id,))
        user_result = cursor.fetchone()
        
        if not user_result:
            cursor.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        current_points = user_result[0]
        
        # For deduction, check if user has enough points
        if "deduct" in user_data and current_points < amount:
            cursor.close()
            conn.close()
            return jsonify({
                "error": "Insufficient points",
                "current_points": current_points,
                "required": amount
            }), 400
        
        # Calculate new points
        new_points = current_points - amount if "deduct" in user_data else current_points + amount
        
        # SQL query to update the points of the user
        update_query = """
            UPDATE user
            SET points = %s
            WHERE user_id = %s
        """

        # Execute the query
        cursor.execute(update_query, (new_points, user_id))
    else:
        return jsonify({"error": "Either 'points', 'deduct', or 'add' must be provided"}), 400

    # Commit the changes
    conn.commit()

    # Check if any row was updated
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    # Get the updated points
    cursor.execute("SELECT points FROM user WHERE user_id = %s", (user_id,))
    updated_points = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()

    return jsonify({
        "message": "Points updated successfully",
        "points": updated_points
    })

@app.route('/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        user_data = request.get_json()
        
        # Build the SQL query dynamically based on provided fields
        update_fields = []
        values = []
        
        if "points" in user_data:
            update_fields.append("points = %s")
            values.append(user_data["points"])
            
        if "subscriber_status" in user_data:
            update_fields.append("subscriber_status = %s")
            values.append(user_data["subscriber_status"])
            
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
            
        update_query = f"""
            UPDATE user 
            SET {', '.join(update_fields)}
            WHERE user_id = %s
        """
        values.append(user_id)
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Failed to connect to database"}), 500

        cursor = conn.cursor()
        cursor.execute(update_query, tuple(values))
        conn.commit()
        
        # Fetch updated user data
        cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
        updated_user = cursor.fetchone()
        
        if updated_user:
            return jsonify({
                "user_id": updated_user[0],
                "name": updated_user[1],
                "phone_number": updated_user[2],
                "email": updated_user[3],
                "address": updated_user[4],
                "points": updated_user[5],
                "subscriber_status": updated_user[6]
            })
        else:
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
