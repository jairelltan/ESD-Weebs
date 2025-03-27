import requests
from flask import Flask, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


# Microservice endpoints (these are URLs to the services)
cart_service_url = "http://127.0.0.1:5008/cart/user"
notification_service_url = 'http://127.0.0.1:5007/notification/bookpayment'

@app.route('/cart/user/bookpayment/<int:user_id>', methods=['DELETE'])
def delete_cart_and_create_notification(user_id):
    # Step 1: Call the Cart Service to delete all cart entries for the given user
    cart_response = requests.delete(f'{cart_service_url}/{user_id}')
    
    if cart_response.status_code != 200:
        return jsonify({"error": "Failed to delete cart entries"}), 500
    
    # Step 2: Call the Notification Service to create a book payment success notification
    notification_payload = {"user_id": user_id}
    notification_response = requests.post(notification_service_url, json=notification_payload)
    
    if notification_response.status_code != 200:
        return jsonify({"error": "Failed to create notification"}), 500
    
    return jsonify({"message": "Cart entries deleted and book payment success notification created successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5020)


