from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import database as db

khata_bp = Blueprint('khata', __name__)

@khata_bp.route('/khata')
def khata_dashboard():
    try:
        customers = db.get_all_customers()
        return render_template('khata.html', customers=customers)
    except Exception as e:
        return render_template('khata.html', customers=[], error=str(e))

# ── JSON API routes used by khata.html ───────────────────────────────────────

@khata_bp.route('/api/khata/customers')
def api_get_customers():
    """Return all customers with balances as JSON."""
    try:
        customers = db.get_all_customers()
        total_outstanding = sum(c['balance'] for c in customers if c['balance'] > 0)
        return jsonify({
            "success": True,
            "customers": customers,
            "total_customers": len(customers),
            "total_outstanding": total_outstanding
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/api/khata/add-customer', methods=['POST'])
def api_add_customer():
    """Add a new customer. Accepts JSON body."""
    try:
        data = request.get_json()
        name = (data.get('name') or '').strip()
        phone = (data.get('phone') or '').strip()
        if not name:
            return jsonify({"success": False, "error": "Name is required"}), 400
        customer_id = db.add_customer(name, phone)
        if customer_id:
            return jsonify({"success": True, "message": "Customer added!", "customer_id": customer_id})
        return jsonify({"success": False, "error": "Failed to add customer"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/api/khata/add-transaction', methods=['POST'])
def api_add_transaction():
    """Add udhar or payment transaction. Accepts JSON body."""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        txn_type = data.get('type')
        amount = data.get('amount')
        note = data.get('note', '')
        if not customer_id or not txn_type or not amount:
            return jsonify({"success": False, "error": "Missing fields"}), 400
        success = db.add_transaction(customer_id, txn_type, float(amount), note)
        if success:
            return jsonify({"success": True, "message": "Transaction recorded!"})
        return jsonify({"success": False, "error": "Failed to record transaction"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/api/khata/transactions/<int:customer_id>')
def api_get_transactions(customer_id):
    """Get all transactions for a customer as JSON."""
    try:
        transactions = db.get_customer_transactions(customer_id)
        return jsonify({"success": True, "transactions": transactions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/api/khata/delete-customer', methods=['POST'])
def api_delete_customer():
    """Delete a customer and all their transactions. Accepts JSON body."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({"success": False, "error": "customer_id required"}), 400
        success = db.delete_customer(int(customer_id))
        if success:
            return jsonify({"success": True, "message": "Customer deleted!"}), 200
        return jsonify({"success": False, "error": "Customer not found in database."}), 404
    except Exception as e:
        print(f"Delete customer error: {e}")
        return jsonify({"success": False, "error": f"DB Error: {str(e)}"}), 500

# ── Legacy form-based routes (kept for backward compatibility) ────────────────

@khata_bp.route('/khata/add_customer', methods=['POST'])
def khata_add_customer():
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        if not name:
            return jsonify({"success": False, "error": "Name is required"}), 400
        customer_id = db.add_customer(name, phone)
        if customer_id:
            return jsonify({"success": True, "message": "Customer added!", "customer_id": customer_id})
        return jsonify({"success": False, "error": "Failed to add customer"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/khata/add_transaction', methods=['POST'])
def khata_add_transaction():
    try:
        customer_id = request.form.get('customer_id')
        txn_type = request.form.get('type')
        amount = request.form.get('amount')
        note = request.form.get('note', '')
        if not customer_id or not txn_type or not amount:
            return jsonify({"success": False, "error": "Missing fields"}), 400
        success = db.add_transaction(customer_id, txn_type, amount, note)
        if success:
            return jsonify({"success": True, "message": "Transaction recorded!"})
        return jsonify({"success": False, "error": "Failed to record transaction"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@khata_bp.route('/khata/customer/<int:customer_id>')
def khata_customer_details(customer_id):
    try:
        customers = db.get_all_customers()
        customer = next((c for c in customers if c['id'] == customer_id), None)
        if not customer:
            return redirect(url_for('khata.khata_dashboard'))
        transactions = db.get_customer_transactions(customer_id)
        return render_template('khata.html', customers=customers,
                               selected_customer=customer,
                               transactions=transactions)
    except Exception as e:
        print(f"Khata customer details error: {e}")
        return redirect(url_for('khata.khata_dashboard'))

@khata_bp.route('/khata/delete_customer/<int:customer_id>')
def khata_delete_customer(customer_id):
    try:
        success = db.delete_customer(customer_id)
        if success:
            return jsonify({"success": True, "message": "Customer deleted"})
        return jsonify({"success": False, "error": "Failed to delete"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
