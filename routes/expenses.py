from flask import Blueprint, render_template, request, jsonify
import database as db

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/expenses')
def expenses_dashboard():
    try:
        expenses = db.get_all_expenses()
        total_expenses = sum(float(e['amount']) for e in expenses)
        return render_template('expenses.html', expenses=expenses, total_expenses=total_expenses)
    except Exception as e:
        return render_template('expenses.html', expenses=[], total_expenses=0, error=str(e))


# ── Route used by the old form-POST approach ─────────────────────────────────
@expenses_bp.route('/expenses/add', methods=['POST'])
def add_expense_route():
    try:
        description = request.form.get('description')
        amount = request.form.get('amount')
        date = request.form.get('date')
        if not description or not amount or not date:
            return jsonify({"success": False, "error": "All fields required"}), 400
        success = db.add_expense(description, amount, date)
        if success:
            return jsonify({"success": True, "message": "Expense added!"})
        return jsonify({"success": False, "error": "Failed to add expense"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── JSON API used by the template fetch() call ───────────────────────────────
@expenses_bp.route('/api/add-expense', methods=['POST'])
def api_add_expense():
    try:
        data = request.get_json()
        description = data.get('description', '').strip()
        amount = data.get('amount')
        date = data.get('date', '').strip()
        if not description or not amount or not date:
            return jsonify({"success": False, "error": "All fields required"}), 400
        success = db.add_expense(description, float(amount), date)
        if success:
            return jsonify({"success": True, "message": "Expense added!"})
        return jsonify({"success": False, "error": "Failed to add expense"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Old GET-based delete (kept for backwards compat) ─────────────────────────
@expenses_bp.route('/expenses/delete/<int:expense_id>')
def delete_expense_route(expense_id):
    try:
        success = db.delete_expense(expense_id)
        if success:
            return jsonify({"success": True, "message": "Expense deleted"})
        return jsonify({"success": False, "error": "Failed to delete"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── REST DELETE used by the template fetch() call ────────────────────────────
@expenses_bp.route('/api/delete-expense/<int:expense_id>', methods=['DELETE', 'GET'])
def api_delete_expense(expense_id):
    try:
        success = db.delete_expense(expense_id)
        if success:
            return jsonify({"success": True, "message": "Expense deleted"})
        return jsonify({"success": False, "error": "Failed to delete"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
