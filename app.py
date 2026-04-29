from flask import Flask, request, render_template, jsonify, session, redirect, url_for
import os
import warnings
from functools import wraps
import database as db
import pickle

# Import Blueprints
from routes.inventory import inventory_bp
from routes.billing import billing_bp
from routes.khata import khata_bp
from routes.expenses import expenses_bp
from routes.analytics import analytics_bp
from routes.ai import ai_bp

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'stocknexus-dev-key-change-in-production')

# Configuration
app.config['UPLOAD_FOLDER'] = 'data_set'
app.config['MODEL_PATH'] = 'trained_model.pkl'
app.config['DATA_PATH'] = 'data_set/data.csv'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Initialize Databases
db.init_db()
db.init_khata_db()
db.init_expense_db()

# Global Authentication Hook
@app.before_request
def require_login():
    """Global authentication check"""
    # Allow login, static files, and public dukaan catalog
    allowed_routes = ['login_page', 'login', 'static', 'billing.dukaan']
    if request.endpoint and request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login_page'))

@app.route('/api/chat-context')
def chat_context_debug():
    """Shows exactly what context the AI chatbot reads from all 4 tables."""
    import database as db
    context = {}

    # Table 1: Inventory
    try:
        df = db.get_all_items()
        context['inventory'] = {
            'total_products': len(df) if df is not None else 0,
            'products': df[['product_name','quantity_stock','minimum_stock_level','total_revenue','expiry_date']].to_dict('records') if df is not None and not df.empty else []
        }
    except Exception as e:
        context['inventory'] = {'error': str(e)}

    # Table 2 & 3: Khata customers + transactions (balance)
    try:
        customers = db.get_all_customers()
        context['khata'] = {
            'total_customers': len(customers),
            'total_outstanding': sum(c['balance'] for c in customers if c['balance'] > 0),
            'customers': customers
        }
    except Exception as e:
        context['khata'] = {'error': str(e)}

    # Table 4: Expenses
    try:
        expenses = db.get_all_expenses()
        context['expenses'] = {
            'total_records': len(expenses),
            'total_amount': sum(float(e['amount']) for e in expenses),
            'records': expenses
        }
    except Exception as e:
        context['expenses'] = {'error': str(e)}

    return jsonify(context)


# Global Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 - Page Not Found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="500 - Internal Server Error"), 500

# Core Authentication Routes
@app.route('/')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('inventory.home'))
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    """Simple authentication logic"""
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    if email and password:
        session['user_id'] = email
        session['user_name'] = email.split('@')[0].capitalize()
        return jsonify({"success": True, "message": "Login successful"})
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# Register Blueprints
app.register_blueprint(inventory_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(khata_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(ai_bp)

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
