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


# ── REST DELETE — matches inventory pattern exactly (POST + JSON body) ─────────
@expenses_bp.route('/api/delete-expense', methods=['POST'])
def api_delete_expense():
    try:
        data = request.get_json(force=True, silent=True) or {}
        expense_id = data.get('expense_id')
        if not expense_id:
            return jsonify({"success": False, "error": "expense_id required"}), 400
        success = db.delete_expense(int(expense_id))
        if success:
            return jsonify({"success": True, "message": "Expense deleted!"}), 200
        return jsonify({"success": False, "error": "Expense not found in database."}), 404
    except Exception as e:
        print(f"Delete expense error: {e}")
        return jsonify({"success": False, "error": f"DB Error: {str(e)}"}), 500

# ── Old URL-based delete (kept for backwards compat) ─────────────────────────
@expenses_bp.route('/api/delete-expense/<int:expense_id>', methods=['DELETE', 'GET', 'POST'])
def api_delete_expense_url(expense_id):
    try:
        success = db.delete_expense(expense_id)
        if success:
            return jsonify({"success": True, "message": "Expense deleted!"}), 200
        return jsonify({"success": False, "error": "Expense not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Debug route: tests full add→delete cycle on live server ──────────────────
@expenses_bp.route('/api/debug-expense-delete')
def debug_expense_delete():
    report = {}
    try:
        # Step 1: Check if DB is active
        report['db_active'] = db.use_db()

        # Step 2: Add a test expense
        add_result = db.add_expense('__DEBUG_DELETE_TEST__', 1.0, '2000-01-01')
        report['add_result'] = str(add_result)

        # Step 3: Get all expenses and find the test one
        expenses = db.get_all_expenses()
        test_exp = next((e for e in expenses if e['description'] == '__DEBUG_DELETE_TEST__'), None)
        report['found_test_expense'] = test_exp
        report['total_expenses'] = len(expenses)

        if test_exp:
            # Step 4: Try to delete it
            del_result = db.delete_expense(int(test_exp['id']))
            report['delete_result'] = str(del_result)
            # Step 5: Verify it's gone
            expenses_after = db.get_all_expenses()
            still_there = any(e['description'] == '__DEBUG_DELETE_TEST__' for e in expenses_after)
            report['still_in_db_after_delete'] = still_there
            report['status'] = 'SUCCESS' if not still_there else 'FAILED - still in DB'
        else:
            report['status'] = 'FAILED - could not find added expense'

    except Exception as e:
        report['exception'] = str(e)
        report['status'] = 'EXCEPTION'

    return jsonify(report)
