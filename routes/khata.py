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
    """Show customer detail - served via khata.html with customer data passed."""
    try:
        customers = db.get_all_customers()
        customer = next((c for c in customers if c['id'] == customer_id), None)
        if not customer:
            return redirect(url_for('khata.khata_dashboard'))
        transactions = db.get_customer_transactions(customer_id)
        # Render main khata page with selected customer context
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
