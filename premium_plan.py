from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('dbURL') or 'mysql+mysqlconnector://root@localhost:3306/premium_plan'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

class PremiumPlan(db.Model):
    __tablename__ = 'premium_plan'

    plan_id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Decimal(10,2), nullable=False)
    duration = db.Column(db.Enum('MONTHLY', 'QUARTERLY', 'YEARLY'), nullable=False)
    features = db.Column(db.Text, nullable=False)

    def __init__(self, plan_name, description, price, duration, features):
        self.plan_name = plan_name
        self.description = description
        self.price = price
        self.duration = duration
        self.features = features

    def json(self):
        return {
            'plan_id': self.plan_id,
            'plan_name': self.plan_name,
            'description': self.description,
            'price': float(self.price),  # Convert Decimal to float for JSON serialization
            'duration': self.duration,
            'features': self.features
        }

# Get all premium plans
@app.route('/premium_plan', methods=['GET'])
def get_all_plans():
    try:
        plans = PremiumPlan.query.all()
        return jsonify({
            'code': 200,
            'data': [plan.json() for plan in plans]
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'Internal server error: {str(e)}'
        }), 500

# Get specific premium plan by ID
@app.route('/premium_plan/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    try:
        plan = PremiumPlan.query.get(plan_id)
        if plan:
            return jsonify({
                'code': 200,
                'data': plan.json()
            }), 200
        return jsonify({
            'code': 404,
            'message': 'Premium plan not found'
        }), 404
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'Internal server error: {str(e)}'
        }), 500

# Initialize database with some default plans if empty
def init_db():
    with app.app_context():
        db.create_all()
        # Check if there are any plans
        if PremiumPlan.query.count() == 0:
            # Add default plans
            default_plans = [
                PremiumPlan(
                    plan_name='Monthly Premium',
                    description='Access all premium features for one month',
                    price=9.99,
                    duration='MONTHLY',
                    features='Unlimited chapter access, Ad-free reading, Early access to new releases'
                ),
                PremiumPlan(
                    plan_name='Quarterly Premium',
                    description='Access all premium features for three months',
                    price=24.99,
                    duration='QUARTERLY',
                    features='Unlimited chapter access, Ad-free reading, Early access to new releases, 10% discount on merchandise'
                ),
                PremiumPlan(
                    plan_name='Yearly Premium',
                    description='Access all premium features for one year',
                    price=89.99,
                    duration='YEARLY',
                    features='Unlimited chapter access, Ad-free reading, Early access to new releases, 15% discount on merchandise, Exclusive seasonal content'
                )
            ]
            for plan in default_plans:
                db.session.add(plan)
            db.session.commit()

if __name__ == '__main__':
    init_db()  # Initialize database and add default plans if needed
    app.run(host='0.0.0.0', port=5004, debug=True) 