from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'receipt'
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
    return "Welcome to the Receipt API!"

# Create a new receipt
@app.route('/receipt', methods=['POST'])
def create_receipt():
    try:
        data = request.get_json()
        
        # Check if all required fields are present
        required_fields = ['user_id', 'transaction_id', 'card_id', 'current_points', 
                         'payment_method', 'subscriber_status', 'billing_address', 
                         'amount']
        
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
        
        # Insert new receipt
        insert_query = """
            INSERT INTO receipt 
            (user_id, transaction_id, card_id, current_points, payment_method, 
             subscriber_status, billing_address, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            data['user_id'],
            data['transaction_id'],
            data['card_id'],
            data['current_points'],
            data['payment_method'],
            data['subscriber_status'],
            data['billing_address'],
            data['amount']
        ))
        
        conn.commit()
        receipt_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 201,
            "data": {
                "receipt_id": receipt_id,
                "message": "Receipt created successfully"
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Get all receipts for a user
@app.route('/receipt/user/<int:user_id>', methods=['GET'])
def get_user_receipts(user_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM receipt 
            WHERE user_id = %s 
            ORDER BY receipt_date DESC
        """, (user_id,))
        
        receipts = cursor.fetchall()
        
        receipts_list = []
        for receipt in receipts:
            receipts_list.append({
                "receipt_id": receipt[0],
                "user_id": receipt[1],
                "transaction_id": receipt[2],
                "card_id": receipt[3],
                "current_points": receipt[4],
                "payment_method": receipt[5],
                "receipt_date": receipt[6].strftime('%Y-%m-%d %H:%M:%S'),
                "subscriber_status": receipt[7],
                "billing_address": receipt[8],
                "GST_amount": float(receipt[9]),
                "total_amount": float(receipt[10])
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 200,
            "data": receipts_list
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Get specific receipt by receipt_id
@app.route('/receipt/<int:receipt_id>', methods=['GET'])
def get_receipt(receipt_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM receipt WHERE receipt_id = %s", (receipt_id,))
        receipt = cursor.fetchone()
        
        if receipt is None:
            return jsonify({
                "code": 404,
                "message": "Receipt not found"
            }), 404
        
        receipt_data = {
            "receipt_id": receipt[0],
            "user_id": receipt[1],
            "transaction_id": receipt[2],
            "card_id": receipt[3],
            "current_points": receipt[4],
            "payment_method": receipt[5],
            "receipt_date": receipt[6].strftime('%Y-%m-%d %H:%M:%S'),
            "subscriber_status": receipt[7],
            "billing_address": receipt[8],
            "GST_amount": float(receipt[9]),
            "total_amount": float(receipt[10])
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 200,
            "data": receipt_data
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

# Get receipt by transaction_id (useful for Stripe webhook integration)
@app.route('/receipt/transaction/<transaction_id>', methods=['GET'])
def get_receipt_by_transaction(transaction_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                "code": 500,
                "message": "Failed to connect to database"
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM receipt WHERE transaction_id = %s", (transaction_id,))
        receipt = cursor.fetchone()
        
        if receipt is None:
            return jsonify({
                "code": 404,
                "message": "Receipt not found"
            }), 404
        
        receipt_data = {
            "receipt_id": receipt[0],
            "user_id": receipt[1],
            "transaction_id": receipt[2],
            "card_id": receipt[3],
            "current_points": receipt[4],
            "payment_method": receipt[5],
            "receipt_date": receipt[6].strftime('%Y-%m-%d %H:%M:%S'),
            "subscriber_status": receipt[7],
            "billing_address": receipt[8],
            "GST_amount": float(receipt[9]),
            "total_amount": float(receipt[10])
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "code": 200,
            "data": receipt_data
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True) 