from flask import Flask, request, jsonify, make_response
import mysql.connector
from datetime import datetime
from flask_cors import CORS

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

# Add specific OPTIONS handlers for crucial endpoints
@app.route('/notification', methods=['OPTIONS'])
def options_notification():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

@app.route('/notification/user/<int:user_id>', methods=['OPTIONS'])
def options_user_notifications(user_id):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept,Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'notification_db'
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
    return "Welcome to the Notification API!"

# Create a new notification
@app.route('/notification', methods=['POST'])
def create_notification():
    try:
        data = request.get_json()
        
        # Check if all required fields are present
        required_fields = ['user_id', 'description']
        
        if not all(field in data for field in required_fields):
            return jsonify({
                "code": 400,
                "message": "Missing required fields"
            }), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500

        cursor = conn.cursor()
        
        # Insert new notification
        insert_query = """
            INSERT INTO notification 
            (user_id, description)
            VALUES (%s, %s)
        """
        
        cursor.execute(insert_query, (
            data['user_id'],
            data['description']
        ))
        
        conn.commit()
        notification_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 201,
            "data": {
                "notification_id": notification_id,
                "message": "Notification created successfully"
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Get all notifications for a user
@app.route('/notification/user/<int:user_id>', methods=['GET'])
def get_user_notifications(user_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notification 
            WHERE user_id = %s 
            ORDER BY time DESC
        """, (user_id,))
        
        notifications = cursor.fetchall()
        
        notifications_list = []
        for notification in notifications:
            notifications_list.append({
                "notification_id": notification[0],
                "user_id": notification[1],
                "description": notification[2],
                "time": notification[3].strftime('%Y-%m-%d %H:%M:%S')
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 200,
            "data": notifications_list
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Create subscription success notification
@app.route('/notification/subscription', methods=['POST'])
def create_subscription_notification():
    try:
        data = request.get_json()
        
        # Check if all required fields are present
        required_fields = ['user_id', 'plan_name']
        
        if not all(field in data for field in required_fields):
            return jsonify({
                "code": 400,
                "message": "Missing required fields"
            }), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500

        cursor = conn.cursor()
        
        # Create subscription success message
        description = f"Payment received successfully! You are now subscribed to {data['plan_name']}."
        
        # Insert new notification
        insert_query = """
            INSERT INTO notification 
            (user_id, description)
            VALUES (%s, %s)
        """
        
        cursor.execute(insert_query, (
            data['user_id'],
            description
        ))
        
        conn.commit()
        notification_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 201,
            "data": {
                "notification_id": notification_id,
                "message": "Subscription notification created successfully"
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500
    

@app.route('/notification/bookpayment', methods=['POST'])
def create_bookpayment_notification():
    try:
        data = request.get_json()
        
        # Ensure required fields exist
        if not data or 'user_id' not in data or 'description' not in data:
            return jsonify({
                "code": 400,
                "message": "Missing required fields: user_id or description"
            }), 400

        user_id = data['user_id']
        description = data['description']

        # Database connection
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500

        cursor = conn.cursor()

        # Insert notification into database
        insert_query = """
            INSERT INTO notification (user_id, description) 
            VALUES (%s, %s)
        """
        cursor.execute(insert_query, (user_id, description))
        
        conn.commit()
        notification_id = cursor.lastrowid

        # Close resources
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 201,
            "data": {
                "notification_id": notification_id,
                "message": "Payment notification created successfully"
            }
        }), 201  # 201 indicates resource creation success

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Create waitlist item added into notification
@app.route('/notification/waitlist', methods=['POST'])
def create_waitlist_notification():
    try:
        data = request.get_json()
        
        # Check if all required fields are present
        required_fields = ['user_id']
        
        if not all(field in data for field in required_fields):
            return jsonify({
                "code": 400,
                "message": "Missing required fields"
            }), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500

        cursor = conn.cursor()
        
        # Create subscription success message
        description = f"A waitlist item is added into the cart."
        
        # Insert new notification
        insert_query = """
            INSERT INTO notification 
            (user_id, description)
            VALUES (%s, %s)
        """
        
        cursor.execute(insert_query, (
            data['user_id'],
            description
        ))
        
        conn.commit()
        notification_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 201,
            "data": {
                "notification_id": notification_id,
                "message": "Item added to waitlist notification created successfully"
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Get specific notification
@app.route('/notification/<int:notification_id>', methods=['GET'])
def get_notification(notification_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notification WHERE notification_id = %s", (notification_id,))
        notification = cursor.fetchone()
        
        if notification is None:
            return jsonify({
                "code": 404,
                "message": "Notification not found"
            }), 404
        
        notification_data = {
            "notification_id": notification[0],
            "user_id": notification[1],
            "description": notification[2],
            "time": notification[3].strftime('%Y-%m-%d %H:%M:%S')
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 200,
            "data": notification_data
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True) 