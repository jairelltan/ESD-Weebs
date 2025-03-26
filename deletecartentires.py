from flask import Flask, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Cart Microservice Base URL
CART_SERVICE_URL = "http://127.0.0.1:5008/cart"

# Inventory Microservice Base URL to get all products
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/IncreaseStock/"

@app.route('/removefromcart/<int:user_id>/<int:product_id>', methods=['DELETE'])
def remove_from_cart(user_id, product_id):
    try:
        # Step 1: Retrieve the cart entry to get its ID and quantity
        cart_response = requests.get(f"{CART_SERVICE_URL}/user/{user_id}/product/{product_id}")
        
        if cart_response.status_code != 200:
            return jsonify({"error": "Cart entry not found"}), 404
        
        cart_data = cart_response.json()
        cart_id = cart_data.get("id")
        quantity = cart_data.get("quantity", 0)

        # Step 2: Delete the cart entry
        delete_response = requests.delete(f"{CART_SERVICE_URL}/{cart_id}")
        
        if delete_response.status_code != 200:
            return jsonify({"error": "Failed to delete cart entry"}), 500
        
        # Step 3: Increase stock in the inventory microservice
        inventory_payload = {
            "product_id": product_id,
            "quantity": quantity
        }
        inventory_response = requests.post(INVENTORY_SERVICE_URL, json=inventory_payload)

        if inventory_response.status_code != 200:
            return jsonify({"error": "Failed to update inventory"}), 500

        return jsonify({"message": "Cart entry deleted and stock updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5016)
