from flask import Flask, request, jsonify, make_response
import mysql.connector
import logging
from decimal import Decimal
import json

# Custom JSON encoder to handle Decimal objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('cart_service')

app = Flask(__name__)
# Set custom JSON encoder for the Flask app
app.json_encoder = CustomJSONEncoder

# Database configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'root_password',
    'database': 'cart_db'
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
        logger.error(f"Database connection error: {err}")
        return None

# Helper function to convert Decimal to float if necessary
def decimal_to_float(data):
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_float(x) for x in data]
    else:
        return data

# Route for home page
@app.route('/')
def home():
    response = make_response("Welcome to the Cart API!")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# Handle OPTIONS requests for all routes
@app.route('/<path:path>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def options_handler(path=''):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response

# Specific OPTIONS handler for cart endpoint with user_id
@app.route('/cart/<int:user_id>', methods=['OPTIONS'])
def cart_user_options(user_id):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,OPTIONS")
    return response

#get all cart items for a specific user_id
@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart_items(user_id):
    logger.debug(f"Getting cart items for user_id: {user_id}")
    conn = get_db_connection()
    if conn is None:
        response = make_response(jsonify({"error": "Failed to connect to database"}), 500)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cart WHERE user_id = %s", (user_id,))
    cart_items = cursor.fetchall()
    
    cart_list = []
    for item in cart_items:
        cart_list.append({
            "id": item[0],
            "user_id": item[1],
            "username": item[2],
            "comic_id": item[3],
            "comic_name": item[4],
            "comic_volume": item[5],
            "price_per_item": decimal_to_float(item[6]) if item[6] else 0,
            "quantity": item[7]
        })
    
    cursor.close()
    conn.close()
    
    logger.debug(f"Returning {len(cart_list)} cart items")
    response = make_response(jsonify(cart_list))
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route('/cart/specificentry/<int:id>', methods=['GET'])
def get_cart_item_hi(id):
    logger.debug(f"Getting specific cart item with id: {id}")
    conn = get_db_connection()
    if conn is None:
        response = make_response(jsonify({"error": "Failed to connect to database"}), 500)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cart WHERE id = %s", (id,))
    cart_item = cursor.fetchone()  
    
    if cart_item is None:
        response = make_response(jsonify({"error": "Cart item not found"}), 404)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cart_data = {
        "cart_id": cart_item[0],       
        "user_id": cart_item[1],
        "username": cart_item[2],
        "comic_id": cart_item[3],     
        "comic_name": cart_item[4],
        "comic_volume": cart_item[5],
        "price_per_item": decimal_to_float(cart_item[6]) if cart_item[6] else 0,
        "quantity": cart_item[7]
    }
    
    cursor.close()
    conn.close()
    
    response = make_response(jsonify(cart_data))
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

#Add or update cart entry (increase quantity if same user_id and comic_id)
@app.route('/cart', methods=['POST'])
def add_or_update_cart_entry():
    data = request.get_json()
    
    if not data:
        response = make_response(jsonify({"error": "No data provided"}), 400)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    required_fields = ["user_id", "username", "comic_id", "comic_name", "comic_volume", "price_per_item", "quantity"]
    if not all(field in data for field in required_fields):
        response = make_response(jsonify({"error": "Missing fields"}), 400)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    conn = get_db_connection()
    if conn is None:
        response = make_response(jsonify({"error": "Failed to connect to database"}), 500)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor = conn.cursor()

    # Check if the entry with the same user_id and comic_id already exists
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND comic_id = %s", (data['user_id'], data['comic_id']))
    existing_item = cursor.fetchone()
    
    if existing_item:
        # If it exists, update the quantity
        new_quantity = existing_item[0] + data['quantity']
        cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND comic_id = %s", 
                       (new_quantity, data['user_id'], data['comic_id']))
        conn.commit()
        response = make_response(jsonify({"message": "Quantity updated successfully"}), 200)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    else:
        #If no exist, insert a new entry
        insert_query = """
        INSERT INTO cart (user_id, username, comic_id, comic_name, comic_volume, price_per_item, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (data["user_id"], data["username"], data["comic_id"], data["comic_name"], 
                                      data["comic_volume"], data["price_per_item"], data["quantity"]))
        conn.commit()
        response = make_response(jsonify({"message": "Cart entry added successfully"}), 200)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

#Delete a cart entry based on id
@app.route('/cart/<int:id>', methods=['DELETE'])
def delete_cart_entry(id):
    logger.debug(f"Deleting cart entry with id: {id}")
    conn = get_db_connection()
    if conn is None:
        response = make_response(jsonify({"error": "Failed to connect to database"}), 500)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id = %s", (id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        response = make_response(jsonify({"error": "Cart entry not found"}), 404)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor.close()
    conn.close()
    
    response = make_response(jsonify({"message": "Cart entry deleted successfully"}), 200)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route('/cart/user/<int:user_id>', methods=['DELETE'])
def delete_all_cart_entries_for_user(user_id):
    logger.debug(f"Deleting all cart entries for user_id: {user_id}")
    conn = get_db_connection()
    if conn is None:
        response = make_response(jsonify({"error": "Failed to connect to database"}), 500)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        response = make_response(jsonify({"error": "No cart entries found for the given user"}), 404)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    cursor.close()
    conn.close()
    
    response = make_response(jsonify({"message": "All cart entries deleted successfully for user"}), 200)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


if __name__ == '__main__':
    logger.info("Starting cart service on port 5008")
    app.run(host='0.0.0.0', port=5008, debug=True)
