from flask import Flask, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Cart Microservice Base URL
CART_SERVICE_URL = "http://127.0.0.1:5008/cart"

# Inventory Microservice Base URL to increase stock
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/IncreaseStock/"

@app.route('/removefromcart/<int:cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    try:
        cart_response = requests.get(f"{CART_SERVICE_URL}/specificentry/{cart_id}")
        
        if cart_response.status_code != 200:
            return jsonify({"error": "Cart entry not found"}), 404
        
        cart_data = cart_response.json()
        
        product_id = cart_data.get("comic_id")  
        quantity = cart_data.get("quantity", 0)
        
        delete_response = requests.delete(f"{CART_SERVICE_URL}/{cart_id}")
        
        if delete_response.status_code != 200:
            return jsonify({"error": "Failed to delete cart entry"}), 500
        
        inventory_url = f"{INVENTORY_SERVICE_URL}{product_id}/{quantity}"
        inventory_response = requests.patch(inventory_url)
        
        if inventory_response.status_code != 200:
            return jsonify({"error": "Failed to update inventory"}), 500
        
        return jsonify({"message": "Cart entry deleted and stock updated successfully"}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Internal service error: " + str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Unexpected error: " + str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5016)
