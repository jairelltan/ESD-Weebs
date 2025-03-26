from flask import Flask, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Cart Microservice Base URL
CART_SERVICE_URL = "http://127.0.0.1:5008/cart"

# Inventory Microservice Base URL to get all products
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/IncreaseStock/"

@app.route('/addtocart/<int:user_id>/<int:product_id>', methods=['GET'])
def delete_entry():


if __name__ == '__main__':
    app.run(debug=True, port=5016)
