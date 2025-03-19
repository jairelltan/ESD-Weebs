from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from enum import Enum
from flask_cors import CORS

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root', 
    'password': '',
    'database': 'user_db'
}

CORS(app)


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

    # Validate if points is provided
    if not user_data or "points" not in user_data:
        return jsonify({"error": "Points not provided"}), 400

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
        SET quantity = %s
        WHERE user_id = %s
    """

    # Execute the query
    cursor.execute(update_query, (points, user_id))

    # Commit the changes
    conn.commit()

    # Check if any row was updated
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    cursor.close()
    conn.close()

    return jsonify({"message": "Points updated successfully"})

# API to update status for a user
@app.route('/user/<int:user_id>/status', methods=['PUT'])
def update_status(user_id):
    # Get the data from the request (assumed to be in JSON format)
    user_data = request.get_json()

    # Validate if status is provided
    if not user_data or "status" not in user_data:
        return jsonify({"error": "Status not provided"}), 400

    status = user_data["status"]

    # Validate if status is valid (you can customize the valid statuses)
    if status not in ["active", "inactive"]:
        return jsonify({"error": "Status must be either 'active' or 'inactive'"}), 400
    
    # Connect to the database
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500

    cursor = conn.cursor()

    # SQL query to update the status of the user
    update_query = """
        UPDATE user
        SET status = %s
        WHERE id = %s
    """

    # Execute the query
    cursor.execute(update_query, (status, user_id))

    # Commit the changes
    conn.commit()

    # Check if any row was updated
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    cursor.close()
    conn.close()

    return jsonify({"message": "Status updated successfully"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
