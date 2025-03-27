from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import stripe

app = Flask(__name__)
CORS(app)

# Initialize Stripe with your secret key
stripe.api_key = 'pk_test_51R6nIRFRwiBVrzVlYE7jVVxhXRxI8S9Vv9OagRWQqhitOwgBF1hoiOKkJr3PDZUvqaxI16rQrdMPx018CMKK9hR00dakf2erY'  

# Service URLs
receipt_URL = os.environ.get('receipt_URL') or "http://localhost:5006/receipt"
notification_URL = os.environ.get('notification_URL') or "http://localhost:5007/notification"

@app.route("/process_payment", methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "code": 400,
                "message": "Invalid JSON input: missing payment details."
            }), 400

        required_fields = ['payment_intent_id', 'amount', 'user_id', 'plan']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400

        payment_intent_id = data['payment_intent_id']
        amount = data['amount']  # amount in cents
        user_id = data['user_id']
        plan = data['plan']

        # 1. Confirm Stripe Payment
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if payment_intent.status != 'succeeded':
                return jsonify({
                    "code": 400,
                    "message": "Payment has not been successfully processed by Stripe."
                }), 400
        except stripe.error.StripeError as e:
            return jsonify({
                "code": 500,
                "message": f"Stripe error: {str(e)}"
            }), 500

        # 2. Create Receipt
        receipt_data = {
            "user_id": user_id,
            "amount": amount / 100,  # Convert cents to dollars
            "subscriber_status": plan.upper(),  # e.g., "MONTHLY" or "YEARLY"
            "payment_intent_id": payment_intent_id
        }

        try:
            receipt_response = requests.post(
                receipt_URL + "/create",
                json=receipt_data
            )
            
            if receipt_response.status_code not in range(200, 300):
                print(f"Receipt creation failed: {receipt_response.text}")
                return jsonify({
                    "code": 500,
                    "message": "Failed to create receipt."
                }), 500
                
            receipt_result = receipt_response.json()
            print(f"Receipt created successfully: {receipt_result}")
            
        except Exception as e:
            print(f"Error creating receipt: {str(e)}")
            return jsonify({
                "code": 500,
                "message": f"Receipt service error: {str(e)}"
            }), 500

        # 3. Send Notification via HTTP
        notification_data = {
            "user_id": user_id,
            "title": "Payment Successful",
            "message": f"Your payment of ${amount/100:.2f} for the {plan} plan was successful.",
            "type": "payment_success"
        }

        try:
            notification_response = requests.post(
                notification_URL + "/create",
                json=notification_data
            )
            
            if notification_response.status_code not in range(200, 300):
                print(f"Notification creation failed: {notification_response.text}")
                # Don't return error here as notification is not critical
            else:
                print(f"Notification sent successfully")
                
        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            # Don't return error here as notification is not critical

        # Return success response
        return jsonify({
            "code": 200,
            "data": {
                "payment_intent_id": payment_intent_id,
                "receipt_id": receipt_result.get("receipt_id"),
                "message": "Payment processed successfully"
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred while processing payment: {str(e)}"
        }), 500

# Error handler for invalid routes
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        "code": 404,
        "message": "The resource was not found."
    }), 404

if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) +
          " for processing payments...")
    app.run(host="0.0.0.0", port=5019, debug=True) 