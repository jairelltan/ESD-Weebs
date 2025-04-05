from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'premium_plan_db'
}

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
    return "Welcome to the Premium Plan API!"

# Get all premium plans
@app.route('/premium_plan', methods=['GET'])
def get_all_plans():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM premium_plan")
    plans = cursor.fetchall()
    
    # Convert the tuple data into a dictionary with appropriate keys
    plans_list = []
    for plan in plans:
        plans_list.append({
            "plan_id": plan[0],
            "plan_name": plan[1],
            "description": plan[2],
            "price": float(plan[3]),  # Convert Decimal to float for JSON serialization
            "duration": plan[4],
            "features": plan[5]
        })
    
    cursor.close()
    conn.close()
    
    return jsonify({
        "code": 200,
        "data": plans_list
    })

# Get a specific plan based on plan ID
@app.route('/premium_plan/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM premium_plan WHERE plan_id = %s", (plan_id,))
    plan = cursor.fetchone()
    
    if plan is None:
        return jsonify({
            "code": 404,
            "message": "Premium plan not found"
        }), 404
    
    # Convert the tuple data into a dictionary with appropriate keys
    plan_data = {
        "plan_id": plan[0],
        "plan_name": plan[1],
        "description": plan[2],
        "price": float(plan[3]),  # Convert Decimal to float for JSON serialization
        "duration": plan[4],
        "features": plan[5]
    }
    
    cursor.close()
    conn.close()
    
    return jsonify({
        "code": 200,
        "data": plan_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True) 