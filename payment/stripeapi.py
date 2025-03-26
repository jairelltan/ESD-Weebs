from flask import Flask, render_template, request, jsonify
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
stripe.api_key = STRIPE_SECRET_KEY

@app.route('/')
def index():
    return render_template('index.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        amount = data.get('amount', 0)  # Amount in cents
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
            },
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 403

if __name__ == '__main__':
    app.run(debug=True, port=5017) 