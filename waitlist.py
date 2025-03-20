from flask import Flask, request, jsonify
import mysql.connector
from enum import Enum
from flask_cors import CORS

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root', 
    'password': '',
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

#get all users
@app.route('/waitlist', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waitlist")
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


if __name__ == '__main__':
    app.run(port=5003, debug=True)
