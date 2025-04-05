from flask import Flask, request, jsonify
import mysql.connector
from enum import Enum
from flask_cors import CORS
from mysql.connector import Error


app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'waitlist_db'
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
    return "Welcome to the Waitlist API!"

#get all waitlistentries
@app.route('/waitlist', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waitlist")
    waitlistentries = cursor.fetchall()
    
    # Convert the tuple data into a dictionary with appropriate keys
    waitlist_list = []
    for waitlist_entry in waitlistentries:
        waitlist_list.append({
            "id": waitlist_entry[0],
            "user_id": waitlist_entry[1],
            "username": waitlist_entry[2],
            "comic_id": waitlist_entry[3],
            "comic_name": waitlist_entry[4],
            "comic_volume": waitlist_entry[5],
            "price_per_item": float(waitlist_entry[6]), 
            "timestamp":waitlist_entry[7]
        })
    
    cursor.close()
    conn.close()
    
    return jsonify(waitlist_list)


@app.route('/waitlist', methods=['POST'])
def add_waitlist_entry():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ["user_id", "username", "comic_id", "comic_name", "comic_volume", "price_per_item", "timestamp"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    
    insert_query = """
    INSERT INTO waitlist (user_id, username, comic_id, comic_name, comic_volume, price_per_item, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    values = (data["user_id"], data["username"], data["comic_id"], data["comic_name"], 
              data["comic_volume"], data["price_per_item"], data["timestamp"])
    
    try:
        cursor.execute(insert_query, values)
        conn.commit()
        return jsonify({"message": "Entry added to waitlist successfully"}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/waitlistdelete/<int:id>', methods=['DELETE'])
def delete_waitlist_entry(id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()

    # Delete the entry based on the provided ID
    delete_query = "DELETE FROM waitlist WHERE id = %s"
    
    try:
        cursor.execute(delete_query, (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({"message": "No entry found with the given ID"}), 404
        
        return jsonify({"message": f"Entry with ID {id} deleted successfully"}), 200
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(port=5003, debug=True)
