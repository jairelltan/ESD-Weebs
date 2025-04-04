import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

STRIPE_SECRET_KEY = 'sk_test_51R6nIRFRwiBVrzVllXMEaH94BfKyNHQy9MPItAU2sj7iUNuwrEx7M7ubfsa5vArOxQs2GwY4DQENYCUvp6WWQZ3400R7hXJYM7' 

app = Flask(__name__)
CORS(app)


# Microservice endpoints
concept_service_url = "http://127.0.0.1:5099/process-payment"  # URL to concept.py
cart_service_url = "http://127.0.0.1:5008/cart/user"  # URL to cart service

@app.route('/payment', methods=['POST'])
def payment_successful():
    try:
        data = request.json
        user_id = data.get('user_id')
        amount = data.get('amount')
        category = data.get('category', '').lower()

        if not user_id or not amount:
            return jsonify({"error": "Missing required fields: user_id or amount"}), 400

        # Step 1: Call processpayment.py to process payment
        concept_response = requests.post(concept_service_url, json={
            "amount": amount,
            "user_id": user_id,
            "category": category
        })

        # Check if processpayment.py responded successfully
        if concept_response.status_code != 200:
            return jsonify({"error": "Failed to process payment in concept service"}), 500

        concept_data = concept_response.json()
        if concept_data.get("error"):
            return jsonify({"error": concept_data.get("error")}), 500
        
        client_secret = concept_data.get("clientSecret")


        # Step 2: If processpayment.py is successful, delete cart entries for the user
        cart_response = requests.delete(f'{cart_service_url}/{user_id}')
        
        if cart_response.status_code != 200:
            return jsonify({"error": "Failed to delete cart entries"}), 500

        return jsonify({
            "message": "Payment processed successfully and cart entries deleted.",
            "clientSecret": client_secret,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5100)  # Ensure this runs on a different port
