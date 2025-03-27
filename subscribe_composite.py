from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# URLs for the microservices
USER_URL = "http://localhost:5000"
PREMIUM_PLAN_URL = "http://localhost:5004"
PAYMENT_URL = "http://localhost:5017"
NOTIFICATION_URL = "http://localhost:5007"

@app.route('/subscribe', methods=['POST'])
def handle_subscription():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        plan_id = data.get('plan_id')

        print(f"Received subscription request for user {user_id} and plan {plan_id}")

        # Step 1: Get user details
        print(f"Fetching user details from {USER_URL}/user/{user_id}")
        user_response = requests.get(f"{USER_URL}/user/{user_id}")
        if user_response.status_code != 200:
            error_msg = f"User service error: {user_response.text}"
            print(error_msg)
            return jsonify({
                "code": 404,
                "message": error_msg
            }), 404
        user_data = user_response.json()
        print(f"User data received: {user_data}")

        # Step 2: Get plan details
        print(f"Fetching plan details from {PREMIUM_PLAN_URL}/premium_plan/{plan_id}")
        plan_response = requests.get(f"{PREMIUM_PLAN_URL}/premium_plan/{plan_id}")
        if plan_response.status_code != 200:
            error_msg = f"Plan service error: {plan_response.text}"
            print(error_msg)
            return jsonify({
                "code": 404,
                "message": error_msg
            }), 404
        plan_data = plan_response.json()['data']
        print(f"Plan data received: {plan_data}")

        # Step 3: Create payment intent
        payment_data = {
            "user_id": user_id,
            "amount": int(float(plan_data['price']) * 100),  # Convert to cents
            "plan_id": plan_id,
            "user_email": user_data['email'],  # For Stripe customer creation
            "plan_name": plan_data['plan_name'],
            "duration": plan_data['duration']
        }
        
        print(f"Creating payment intent at {PAYMENT_URL}/create-payment-intent with data: {payment_data}")
        payment_response = requests.post(
            f"{PAYMENT_URL}/create-payment-intent", 
            json=payment_data
        )
        
        if payment_response.status_code != 200:
            error_msg = f"Payment service error: {payment_response.text}"
            print(error_msg)
            return jsonify({
                "code": 500,
                "message": error_msg
            }), 500

        payment_data = payment_response.json()
        print(f"Payment intent created: {payment_data}")

        # Return the client secret and plan details
        return jsonify({
            "code": 200,
            "data": {
                "client_secret": payment_data['clientSecret'],
                "plan_details": plan_data,
                "amount": int(float(plan_data['price']) * 100)  # Use the amount we calculated earlier
            }
        })

    except Exception as e:
        error_msg = f"Internal server error: {str(e)}"
        print(error_msg)
        return jsonify({
            "code": 500,
            "message": error_msg
        }), 500

@app.route('/subscribe/complete', methods=['POST'])
def complete_subscription():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        duration = data.get('duration')
        transaction_id = data.get('transaction_id')

        print(f"Completing subscription for user {user_id} with {duration} plan")

        # Step 1: Update user points and subscription status
        update_data = {
            "points": 99999999,
            "subscriber_status": duration.upper()  # Convert to uppercase to match enum values
        }
        print(f"Updating user data: {update_data}")
        user_response = requests.put(f"{USER_URL}/user/{user_id}", json=update_data)
        if user_response.status_code != 200:
            error_msg = f"Failed to update user: {user_response.text}"
            print(error_msg)
            return jsonify({"code": 500, "message": error_msg}), 500

        # Step 2: Create receipt
        receipt_data = {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "card_id": 1,  # Default card ID
            "current_points": 99999999,
            "payment_method": "CREDIT_CARD",
            "subscriber_status": "active",
            "billing_address": "Default Address",  # Should be gotten from user data in production
            "GST_amount": 0.00,  # Should be calculated based on plan price
            "total_amount": 0.00  # Should be gotten from plan price
        }
        print(f"Creating receipt: {receipt_data}")
        receipt_response = requests.post(f"{PAYMENT_URL}/receipt", json=receipt_data)
        if receipt_response.status_code != 201:
            print(f"Warning: Failed to create receipt: {receipt_response.text}")
            # Don't return error as receipt is not critical

        # Step 3: Send notification
        notification_data = {
            "user_id": user_id,
            "title": "Subscription Activated",
            "message": f"Your {duration.lower()} subscription has been activated successfully!"
        }
        print(f"Sending notification: {notification_data}")
        notification_response = requests.post(f"{NOTIFICATION_URL}/notification", json=notification_data)
        if notification_response.status_code != 201:
            print(f"Warning: Failed to send notification: {notification_response.text}")
            # Don't return error as notification is not critical

        return jsonify({
            "code": 200,
            "message": "Subscription activated successfully"
        })

    except Exception as e:
        error_msg = f"Failed to complete subscription: {str(e)}"
        print(error_msg)
        return jsonify({
            "code": 500,
            "message": error_msg
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5018, debug=True) 