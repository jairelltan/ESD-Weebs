import time
import threading
from flask import Flask, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Event to manage the task execution
task_event = threading.Event()

# Waitlist Microservice Base URL
WAITLIST_SERVICE_URL = "http://127.0.0.1:5003/waitlist"

# Inventory Microservice Base URL to get all products
INVENTORY_SERVICE_URL = "https://personal-dwnxuxog.outsystemscloud.com/InventoryAtomicMicroservice/rest/RESTAPI/GetAllProducts"

# AddtoCart Microservice Base URL to add items to the cart
CART_SERVICE_URL = "http://127.0.0.1:5009/addtocart"

# Waitlist Delete Microservice URL
WAITLIST_DELETE_URL = "http://127.0.0.1:5003/waitlistdelete"


def process_waitlist_and_add_to_cart():
    # Ensure the task runs only once and doesn't restart if it is already running
    if task_event.is_set():
        return

    task_event.set()  # Mark the task as running

    # Fetch the waitlist
    waitlist_response = requests.get(WAITLIST_SERVICE_URL)
    if waitlist_response.status_code != 200:
        print(f"Error fetching waitlist: {waitlist_response.status_code}")
        task_event.clear()  # Clear event flag if an error happens
        return

    waitlist_data = waitlist_response.json()
    print(f"Waitlist fetched: {len(waitlist_data)} records")

    # Fetch all products from the inventory
    inventory_response = requests.get(INVENTORY_SERVICE_URL)
    if inventory_response.status_code != 200:
        print(f"Error fetching inventory: {inventory_response.status_code}")
        task_event.clear()  # Clear event flag if an error happens
        return

    inventory_data = inventory_response.json()
    print(f"Inventory fetched: {len(inventory_data['Products'])} products")

    # Sort by timestamp. Just in case
    waitlist_data_sorted = sorted(waitlist_data, key=lambda x: x['timestamp'])

    # Process each product in the inventory
    for product in inventory_data['Products']:
        comic_id = product['Id']
        available_stock = product['quantity_in_stock']

        if available_stock > 0:
            print(f"Processing product: {product['comic_name']} (ID: {comic_id}), Stock: {available_stock}")

            # Get the waitlist entries for this product
            product_waitlist = [entry for entry in waitlist_data_sorted if entry['comic_id'] == comic_id]

            # Process as many entries as the stock quantity. This is important cause without this it just adds all of the wishlist stuff into the cart db
            entries_to_process = product_waitlist[:available_stock]

            for entry in entries_to_process:
                user_id = entry.get('user_id')
                print(f"Adding product to cart for user {user_id}...")

                # Add a 3-second delay before each request
                time.sleep(3)

                cart_response = requests.get(f"{CART_SERVICE_URL}/{user_id}/{comic_id}")
                if cart_response.status_code != 200:
                    print(f"Failed to update cart for user {user_id}: {cart_response.status_code}")
                    continue

                available_stock -= 1  # ✅ Immediately update stock after adding to cart

                # Add a 3-second delay before the waitlist deletion request
                time.sleep(3)  # Wait for 3 seconds before making the waitlist delete request

                # Delete the waitlist entry after adding the product to the cart
                waitlist_delete_url = f"{WAITLIST_DELETE_URL}/{entry['id']}"
                waitlist_delete_response = requests.delete(waitlist_delete_url)
                if waitlist_delete_response.status_code != 200:
                    print(f"Failed to delete waitlist entry for user {user_id}: {waitlist_delete_response.status_code}")

                # Remove processed entry
                waitlist_data_sorted.remove(entry)

    # Clear the task_event flag after task completion
    task_event.clear()
    print("Task completed!")


@app.route('/start_task', methods=['POST'])
def start_task():
    # Check if the task is already running
    if task_event.is_set():
        return jsonify({"message": "Task is already running. Please wait."}), 400
    else:
        # Start the task in a separate thread
        threading.Thread(target=process_waitlist_and_add_to_cart).start()
        return jsonify({"message": "Task started successfully!"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5010)
