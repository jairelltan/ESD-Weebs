from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cart_db'
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
    return "Welcome to the Cart API!"

#get all cart items for a specific user_id
@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart_items(user_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
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
            "price_per_item": item[6],
            "quantity": item[7]
        })
    
    cursor.close()
    conn.close()
    
    return jsonify(cart_list)

#Add or update cart entry (increase quantity if same user_id and comic_id)
@app.route('/cart', methods=['POST'])
def add_or_update_cart_entry():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ["user_id", "username", "comic_id", "comic_name", "comic_volume", "price_per_item", "quantity"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
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
        return jsonify({"message": "Quantity updated successfully"}), 200
    else:
        #If no exist, insert a new entry
        insert_query = """
        INSERT INTO cart (user_id, username, comic_id, comic_name, comic_volume, price_per_item, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (data["user_id"], data["username"], data["comic_id"], data["comic_name"], 
                                      data["comic_volume"], data["price_per_item"], data["quantity"]))
        conn.commit()
        return jsonify({"message": "Cart entry added successfully"}), 200

#Delete a cart entry based on id
@app.route('/cart/<int:id>', methods=['DELETE'])
def delete_cart_entry(id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id = %s", (id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        return jsonify({"error": "Cart entry not found"}), 404
    
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Cart entry deleted successfully"}), 200

#Reduce the quantity of a cart entry based on id
@app.route('/cart/<int:id>/reduce', methods=['PATCH'])
def reduce_quantity(id):
    data = request.get_json()
    
    if "quantity" not in data:
        return jsonify({"error": "Quantity not provided"}), 400
    
    quantity_to_reduce = data["quantity"]
    
    if quantity_to_reduce <= 0:
        return jsonify({"error": "Quantity must be greater than zero"}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to database"}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE id = %s", (id,))
    cart_item = cursor.fetchone()
    
    if not cart_item:
        return jsonify({"error": "Cart entry not found"}), 404
    
    new_quantity = cart_item[0] - quantity_to_reduce
    
    if new_quantity < 0:
        return jsonify({"error": "Cannot reduce quantity below zero"}), 400
    
    cursor.execute("UPDATE cart SET quantity = %s WHERE id = %s", (new_quantity, id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Quantity reduced successfully"}), 200

if __name__ == '__main__':
    app.run(port=5008, debug=True)
