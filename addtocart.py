from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# User Microservice Base URL
USER_SERVICE_URL = "http://127.0.0.1:5000/user"

# Inventory Microservice Base URL
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/GetProductbyID"

# Cart Microservice Base URL
CART_SERVICE_URL = "http://127.0.0.1:5008/cart"


@app.route('/addtocart/<int:user_id>/<int:product_id>', methods=['GET'])
def get_composite_data(user_id, product_id):
    # Fetch user data
    user_response = requests.get(f"{USER_SERVICE_URL}/{user_id}")
    if user_response.status_code != 200:
        return jsonify({"error": "User not found"}), user_response.status_code
    user_data = user_response.json()

    # Fetch product data
    inventory_response = requests.get(f"{INVENTORY_SERVICE_URL}/{product_id}")
    if inventory_response.status_code != 200:
        return jsonify({"error": "Product not found"}), inventory_response.status_code
    
    inventory_data = inventory_response.json()

    # Ensure the response contains a valid product list
    if "Products" in inventory_data and len(inventory_data["Products"]) > 0:
        product = inventory_data["Products"][0]  # Extract the first product because it is a list
    else:
        return jsonify({"error": "No product data found"}), 404

    # Aggregate Data with selected fields from the user db and the outsystemsdb
    composite_data = {
        "user_id": user_data.get("id"),
        "username": user_data.get("name"),  
        "comic_id": product.get("Id"),
        "comic_name": product.get("comic_name"),
        "comic_volume": product.get("volume_name"),
        "price_per_item": product.get("price_per_item"),
        "quantity": 1
    }

    print(composite_data)

    # Send the composite data to the cart service to add/update it
    cart_response = requests.post(CART_SERVICE_URL, json=composite_data)
    if cart_response.status_code != 200:
        return jsonify({"error": "Failed to update cart"}), cart_response.status_code

    # Return the updated cart data or success confirmation
    cart_data = cart_response.json()
    return jsonify({"message": "Item added/updated in cart", "cart_data": cart_data})

if __name__ == '__main__':
    app.run(debug=True, port=5009)

