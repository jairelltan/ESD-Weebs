# Stripe Payment Integration

This is a simple Flask application that integrates Stripe payments into a web application.

## Setup Instructions

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. The application is already configured with your Stripe test keys in `config.py`.

3. Run the Flask application:
```bash
python app.py
```

4. Open your web browser and navigate to `http://localhost:5000`

## Testing the Payment System

You can use the following test card numbers:
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002
- Any future expiry date
- Any 3-digit CVC
- Any postal code

## Security Notes

- This is using test keys. For production, make sure to:
  1. Use your live Stripe keys
  2. Store keys in environment variables
  3. Enable HTTPS
  4. Implement proper error handling and logging
  5. Add additional security measures like rate limiting

## Features

- Modern, responsive UI
- Real-time card validation
- Error handling
- Success confirmation
- Secure payment processing 