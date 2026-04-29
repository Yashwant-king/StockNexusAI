from flask import Blueprint, render_template, request, jsonify
import database as db

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/expenses')
def expenses_dashboard():
    try:
        expenses = db.get_all_expenses()
        total_expense = sum(float(e['amount']) for e in expenses)
        return render_template('expenses.html', expenses=expenses, total_expense=total_expense)
    except Exception as e:
        return render_template('expenses.html', expenses=[], total_expense=0, error=str(e))

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

@expenses_bp.route('/expenses/delete/<int:expense_id>')
def delete_expense_route(expense_id):
    try:
        success = db.delete_expense(expense_id)
        if success:
            return jsonify({"success": True, "message": "Expense deleted"})
        return jsonify({"success": False, "error": "Failed to delete"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
