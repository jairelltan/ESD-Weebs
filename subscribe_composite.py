from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
import json

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
payment_composite_URL = os.environ.get('payment_composite_URL') or "http://localhost:5021/process_payment"

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
        print(f"Received completion data: {data}")  # Log received data
        
        user_id = data.get('user_id')
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

    except Exception as e:
        import traceback
        error_msg = f"Internal server error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        return jsonify({
            "code": 500,
            "message": f"Failed to complete subscription: {str(e)}"
        }), 500

@app.route("/subscribe/<string:user_id>", methods=['POST'])
def subscribe_user(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "code": 400,
                "message": "Invalid JSON input: missing subscription details."
            }), 400

        required_fields = ['payment_intent_id', 'amount', 'plan']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400

        payment_intent_id = data['payment_intent_id']
        amount = data['amount']  # amount in cents
        plan = data['plan']

        # 1. Process payment through payment composite service
        try:
            payment_response = requests.post(
                payment_composite_URL,
                json={
                    "payment_intent_id": payment_intent_id,
                    "amount": amount,
                    "user_id": user_id,
                    "plan": plan
                }
            )
            
            if payment_response.status_code not in range(200, 300):
                return jsonify({
                    "code": 500,
                    "message": "Payment processing failed."
                }), 500
                
            payment_result = payment_response.json()
            print(f"Payment processed successfully: {payment_result}")
            
        except Exception as e:
            return jsonify({
                "code": 500,
                "message": f"Payment composite service error: {str(e)}"
            }), 500

        # 2. Update user's premium status
        try:
            premium_response = requests.post(
                f"{premium_URL}/create",
                json={
                    "user_id": user_id,
                    "plan": plan
                }
            )
            
            if premium_response.status_code not in range(200, 300):
                return jsonify({
                    "code": 500,
                    "message": "Failed to update premium status."
                }), 500
                
            premium_result = premium_response.json()
            print(f"Premium status updated successfully: {premium_result}")
            
        except Exception as e:
            return jsonify({
                "code": 500,
                "message": f"Premium service error: {str(e)}"
            }), 500

        # 3. Update user points based on the plan
        points_to_add = 99999999 if plan.upper() in ["MONTHLY", "YEARLY"] else 0
        
        try:
            user_response = requests.put(
                f"{user_URL}/{user_id}/points",
                json={"points": points_to_add}
            )
            
            if user_response.status_code not in range(200, 300):
                return jsonify({
                    "code": 500,
                    "message": "Failed to update user points."
                }), 500
                
            user_result = user_response.json()
            print(f"User points updated successfully: {user_result}")
            
        except Exception as e:
            return jsonify({
                "code": 500,
                "message": f"User service error: {str(e)}"
            }), 500

        # Return success response
        return jsonify({
            "code": 200,
            "data": {
                "payment_intent_id": payment_intent_id,
                "receipt_id": payment_result["data"]["receipt_id"],
                "message": "Subscription activated successfully",
                "points": points_to_add
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred while processing subscription: {str(e)}"
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