import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Microservice endpoints
stripe_service_url = "http://127.0.0.1:5017/create-payment-intent"
notification_service_url = "http://127.0.0.1:5007/notification/bookpayment"

@app.route('/process-payment', methods=['POST'])
def process_payment():
    try:
        data = request.json
        amount = data.get('amount') 
        user_id = data.get('user_id')
        category = data.get('category', '').lower() 

        if not amount or not user_id:
            return jsonify({"error": "Missing required fields: amount or user_id"}), 400

        # Step 1: Call Stripe Service to create a payment intent
        stripe_response = requests.post(stripe_service_url, json={"amount": amount})

        if stripe_response.status_code != 200:
            return jsonify({"error": "Failed to create payment intent"}), 500

        stripe_data = stripe_response.json()
        client_secret = stripe_data.get("clientSecret")

        if not client_secret:
            return jsonify({"error": "Stripe response did not include clientSecret"}), 500

        # Step 2: Call Notification Service with appropriate message
        if category == "book":
            description = "Payment received successfully! Your books will arrive soon."
        else:
            description = "Subscription successful! Enjoy your access."

        notification_payload = {"user_id": user_id, "description": description}
        notification_response = requests.post(notification_service_url, json=notification_payload)

        if notification_response.status_code != 201:
            return jsonify({"error": "Failed to create payment success notification"}), 500

        return jsonify({
            "message": "Payment initiated successfully, and notification sent.",
            "clientSecret": client_secret
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5099)
