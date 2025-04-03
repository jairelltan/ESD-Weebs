from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import pika
import json
import requests

app = Flask(__name__)
CORS(app)

# User Microservice Base URL
USER_SERVICE_URL = "http://127.0.0.1:5000/user"

# Inventory Microservice Base URL
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/GetProductbyID"

# RabbitMQ setup
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'fcfs_queue'

def connect_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)  # Make the queue durable
    return connection, channel

def publish_to_queue(channel, data):
    message = json.dumps(data)
    print(f" [x] Ready to send message: {message}")  # Log the message before sending it
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )
    print(f" [x] Sent data to RabbitMQ: {data}")

@app.route('/addtowaitlist/<int:user_id>/<int:product_id>', methods=['GET'])
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
        "timestamp": datetime.utcnow().isoformat()
    }

    # Send data to RabbitMQ (First-Come, First-Serve)
    connection, channel = connect_to_rabbitmq()
    publish_to_queue(channel, composite_data)
    connection.close()

    return jsonify(composite_data)

if __name__ == '__main__':
    app.run(debug=True, port=5002)

