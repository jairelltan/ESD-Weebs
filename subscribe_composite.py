from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
import json
import stripe


app = Flask(__name__)
CORS(app)

# URLs for the microservices
USER_URL = "http://localhost:5000"
PREMIUM_PLAN_URL = "http://localhost:5004"
PAYMENT_URL = "http://localhost:5017"
NOTIFICATION_URL = "http://localhost:5007"
RECEIPT_URL = "http://localhost:5006"

# Service URLs
user_URL = os.environ.get('user_URL') or "http://localhost:5000/user"
premium_URL = os.environ.get('premium_URL') or "http://localhost:5004/premium"
payment_composite_URL = os.environ.get('payment_composite_URL') or "http://localhost:5019/process_payment"

stripe.api_key = 'pk_test_51R6nIRFRwiBVrzVlYE7jVVxhXRxI8S9Vv9OagRWQqhitOwgBF1hoiOKkJr3PDZUvqaxI16rQrdMPx018CMKK9hR00dakf2erY'  


@app.route('/subscribe', methods=['POST'])
def handle_subscription():
    try:
        data = request.get_json()
        action = data.get('action', 'initiate')  # Default to initiate if not specified
        user_id = data.get('user_id')

        print(f"Received {action} subscription request for user {user_id}")

        if action == 'initiate':
            plan_id = data.get('plan_id')
            
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

        elif action == 'complete':
            duration = data.get('duration')
            transaction_id = data.get('transaction_id')
            amount = data.get('amount', 0)
            plan_name = data.get('plan_name', 'Unknown Plan')

            print(f"Processing subscription completion for user {user_id} with {duration} plan")

            # Step 1: Get user data
            print(f"Fetching user data from {USER_URL}/user/{user_id}")
            user_response = requests.get(f"{USER_URL}/user/{user_id}")
            print(f"User service response status: {user_response.status_code}")
            print(f"User service response body: {user_response.text}")
            
            if user_response.status_code != 200:
                error_msg = f"Failed to fetch user data: {user_response.text}"
                print(error_msg)
                return jsonify({"code": 500, "message": error_msg}), 500
                
            user_data = user_response.json()
            print(f"User data retrieved: {user_data}")

            # Step 2: Update user points and subscription status
            update_data = {
                "points": 99999999,  # Unlimited points
                "subscriber_status": duration.upper()  # Convert to uppercase to match enum values
            }
            print(f"Updating user data at {USER_URL}/user/{user_id} with data: {update_data}")
            user_response = requests.put(f"{USER_URL}/user/{user_id}", json=update_data)
            print(f"User update response status: {user_response.status_code}")
            print(f"User update response body: {user_response.text}")
            
            if user_response.status_code != 200:
                error_msg = f"Failed to update user: {user_response.text}"
                print(error_msg)
                return jsonify({"code": 500, "message": error_msg}), 500

            # Step 3: Create receipt
            amount_decimal = float(amount) / 100  # Convert cents to dollars

            receipt_data = {
                "user_id": user_id,
                "transaction_id": transaction_id,
                "card_id": 1,
                "current_points": 99999999,
                "payment_method": "CREDIT_CARD",
                "subscriber_status": duration,  # Send the duration as the status (e.g. MONTHLY, YEARLY)
                "billing_address": user_data.get('address', 'Default Address'),
                "amount": amount_decimal
            }
            print(f"Creating receipt with data: {receipt_data}")
            receipt_response = requests.post(f"{RECEIPT_URL}/receipt", json=receipt_data)
            print(f"Receipt creation response status: {receipt_response.status_code}")
            print(f"Receipt creation response body: {receipt_response.text}")
            
            if receipt_response.status_code != 201:
                error_msg = f"Failed to create receipt: {receipt_response.text}"
                print(error_msg)
                # Don't return error as receipt is not critical, but log it
                print("Continuing despite receipt creation failure")

            # Step 4: Create Notification
            notification_data = {
                "user_id": user_id,
                "description": duration + " subscribed!"
            }
            
            print(f"Creating notification with data: {notification_data}")
            notification_response = requests.post(f"{NOTIFICATION_URL}/notification", json=notification_data)
            print(f"Notification creation response status: {notification_response.status_code}")
            print(f"Notification creation response body: {notification_response.text}")
                
            return jsonify({
                "code": 200,
                "message": "Subscription activated successfully",
                "data": {
                    "user_id": user_id,
                    "points": 99999999,
                    "subscriber_status": duration.upper(),
                    "transaction_id": transaction_id
                }
            })

        else:
            return jsonify({
                "code": 400,
                "message": f"Invalid action: {action}"
            }), 400

    except Exception as e:
        import traceback
        error_msg = f"Internal server error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        return jsonify({
            "code": 500,
            "message": f"Failed to process subscription: {str(e)}"
        }), 500

# Error handler for invalid routes
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        "code": 404,
        "message": "The resource was not found."
    }), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5018, debug=True) 