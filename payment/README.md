# Payment Service with Stripe Integration

## Overview
This service handles all payment-related operations using Stripe's API. It runs on port 5017 and serves as an atomic service in the microservices architecture.

## Service Type
- **Type**: Atomic Service with External API Integration
- **Port**: 5017
- **Main File**: stripeapi.py

## Endpoints

### 1. Create Payment Intent
- **Endpoint**: POST `/create-payment-intent`
- **Description**: Creates a Stripe payment intent and returns the client secret
- **Required Fields**:
  - user_id: User identifier
  - amount: Payment amount in cents
  - user_email: Customer email for Stripe customer creation
  - plan_name: Name of the subscription plan
  - duration: Duration of the subscription (MONTHLY/YEARLY)
- **Response**: 
  ```json
  {
    "clientSecret": "pi_xxxxx_secret_xxxxx",
    "amount": 1000
  }
  ```

## Stripe Integration Features
- Customer Management
  - Creates new Stripe customers for first-time subscribers
  - Associates payment methods with customers
- Payment Processing
  - Handles payment intent creation
  - Manages payment confirmation
  - Processes subscription payments
- Security
  - Securely handles payment information
  - Uses Stripe's client secret for secure client-side confirmation

## Environment Setup
1. Requires Stripe API keys
2. Set up in stripeapi.py:
   ```python
   stripe.api_key = 'your_stripe_secret_key'
   ```

## Dependencies
- stripe
- flask
- flask_cors
- requests

## Error Handling
- Handles Stripe API errors
- Returns appropriate HTTP status codes
- Provides detailed error messages for debugging

## Integration with Other Services
This service is called by the Subscribe Service (composite) to:
1. Create payment intents for new subscriptions
2. Process subscription payments
3. Manage customer payment information 