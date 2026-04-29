from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
import database as db
from datetime import datetime

ai_bp = Blueprint('ai', __name__)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')


@ai_bp.route('/ai_assistant')
def ai_assistant_page():
    # Redirect to dashboard where the AI chat panel is embedded
    return redirect(url_for('inventory.home'))


@ai_bp.route('/api/chat', methods=['POST'])
def AI_Chat():
    try:
        from groq import Groq
        data = request.get_json()
        user_query = data.get('message', data.get('query', ''))
        if not user_query:
            return jsonify({"success": True, "reply": "I didn't hear anything. How can I help you today?"})

        # ── 1. INVENTORY CONTEXT ─────────────────────────────────────────────
        inventory_df = db.get_all_items()
        inv_count = len(inventory_df) if inventory_df is not None else 0
        inv_summary = f"INVENTORY: {inv_count} products total."
        if inventory_df is not None and not inventory_df.empty:
            low_stock = inventory_df[
                inventory_df['quantity_stock'].astype(float) <= inventory_df['minimum_stock_level'].astype(float)
            ]
            total_rev = float(inventory_df['total_revenue'].astype(float).sum())
            inv_summary += f" Low stock: {len(low_stock)} items. Total revenue: ₹{total_rev:,.2f}."
            # List all products with stock
            product_lines = []
            for _, row in inventory_df.iterrows():
                product_lines.append(
                    f"{row.get('product_name','?')} (stock:{row.get('quantity_stock',0)}, min:{row.get('minimum_stock_level',0)}, expiry:{row.get('expiry_date','N/A')})"
                )
            inv_summary += f" Products: {'; '.join(product_lines[:20])}."  # limit to 20

        # ── 2. KHATA CONTEXT ─────────────────────────────────────────────────
        khata_summary = "KHATA (CREDIT BOOK): "
        try:
            customers = db.get_all_customers()
            if customers:
                total_outstanding = sum(c['balance'] for c in customers if c['balance'] > 0)
                fully_paid = sum(1 for c in customers if c['balance'] <= 0)
                khata_summary += (
                    f"{len(customers)} customers. "
                    f"Total outstanding dues: ₹{total_outstanding:,.2f}. "
                    f"Fully paid customers: {fully_paid}. "
                )
                # List customers with balance
                due_customers = [c for c in customers if c['balance'] > 0]
                if due_customers:
                    cust_lines = [f"{c['name']} owes ₹{c['balance']:,.2f}" for c in due_customers[:10]]
                    khata_summary += f"Customers with dues: {'; '.join(cust_lines)}."
            else:
                khata_summary += "No customers yet."
        except Exception as e:
            khata_summary += f"Could not load khata data ({e})."

        # ── 3. EXPENSES CONTEXT ──────────────────────────────────────────────
        expenses_summary = "EXPENSES: "
        try:
            expenses = db.get_all_expenses()
            if expenses:
                total_expenses = sum(float(e['amount']) for e in expenses)
                expenses_summary += f"{len(expenses)} expense records. Total spent: ₹{total_expenses:,.2f}. "
                recent = expenses[:5]
                exp_lines = [f"{e.get('description','?')} ₹{float(e.get('amount',0)):,.2f}" for e in recent]
                expenses_summary += f"Recent expenses: {'; '.join(exp_lines)}."
            else:
                expenses_summary += "No expenses recorded yet."
        except Exception as e:
            expenses_summary += f"Could not load expense data ({e})."

        # ── 4. BUILD FULL CONTEXT ────────────────────────────────────────────
        full_context = f"{inv_summary}\n{khata_summary}\n{expenses_summary}"

        if not GROQ_API_KEY:
            reply = f"Groq API key not set. Here is your data summary:\n{full_context}"
            return jsonify({"success": True, "reply": reply})

        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are StockNexus AI, a helpful and friendly business assistant for an Indian Kirana "
                        "(grocery) store. You have full access to the store's data including inventory, "
                        "customer credit book (khata), and expenses. "
                        "Respond in the same language the user writes in (Hindi or English or Hinglish). "
                        "Be concise, practical, and helpful. Use ₹ for currency. "
                        "Here is the current live data from all tables:\n\n"
                        f"{full_context}"
                    )
                },
                {"role": "user", "content": user_query}
            ],
            max_tokens=600,
            temperature=0.7
        )
        reply = completion.choices[0].message.content
        return jsonify({"success": True, "reply": reply})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})



@ai_bp.route('/api/daily-report')
def daily_report():
    """Generate a WhatsApp-ready daily business report."""
    try:
        inventory_df = db.get_all_items()
        customers = db.get_all_customers()

        total_products = len(inventory_df) if inventory_df is not None else 0
        total_revenue = 0.0
        low_stock_count = 0
        near_expiry_count = 0

        if inventory_df is not None and not inventory_df.empty:
            total_revenue = float(inventory_df['total_revenue'].astype(float).sum())
            low_stock_count = int(len(inventory_df[
                inventory_df['quantity_stock'].astype(float) <= inventory_df['minimum_stock_level'].astype(float)
            ]))
            # Count near expiry (within 7 days)
            today_ts = datetime.now()
            for _, row in inventory_df.iterrows():
                exp_str = str(row.get('expiry_date', ''))
                for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                    try:
                        exp_date = datetime.strptime(exp_str, fmt)
                        if 0 <= (exp_date - today_ts).days <= 7:
                            near_expiry_count += 1
                        break
                    except Exception:
                        continue

        total_pending = sum(float(c.get('balance', 0)) for c in customers if float(c.get('balance', 0)) > 0)

        today_str = datetime.now().strftime('%d %b %Y')

        report = (
            f"\U0001f680 *KIRANA STORE DAILY REPORT*\n"
            f"\U0001f4c5 Date: {today_str}\n\n"
            f"\U0001f4e6 *Inventory Summary:*\n"
            f"\u2022 Total Products: {total_products}\n"
            f"\u2022 Low Stock Alerts: {low_stock_count}\n"
            f"\u2022 Near Expiry Items: {near_expiry_count}\n\n"
            f"\U0001f4b0 *Revenue:*\n"
            f"\u2022 Total Revenue: \u20b9{total_revenue:,.2f}\n\n"
            f"\U0001f4d2 *Khata (Credit Book):*\n"
            f"\u2022 Pending Dues: \u20b9{total_pending:,.2f}\n\n"
            f"_Generated by StockNexus AI_ \U0001f916"
        )

        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@ai_bp.route('/api/discount-suggestions')
def discount_suggestions():
    """Return AI-recommended discounts for near-expiry items."""
    try:
        inventory_df = db.get_all_items()
        suggestions = []

        if inventory_df is not None and not inventory_df.empty:
            today_ts = datetime.now()
            for _, row in inventory_df.iterrows():
                exp_str = str(row.get('expiry_date', ''))
                for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                    try:
                        exp_date = datetime.strptime(exp_str, fmt)
                        days_left = (exp_date - today_ts).days
                        if 0 < days_left <= 10:
                            stock = int(float(row.get('quantity_stock', 0)))
                            if stock > 0:
                                original_price = float(row.get('total_revenue', 0))
                                discount = int(min(50, max(15, 55 - days_left * 5)))
                                sale_price = original_price * (1 - discount / 100)
                                suggestions.append({
                                    'product_name': str(row.get('product_name', '')),
                                    'days_left': days_left,
                                    'stock': stock,
                                    'original_price': original_price,
                                    'discount': discount,
                                    'sale_price': round(sale_price, 2),
                                    'estimated_savings': round(sale_price * stock, 2)
                                })
                        break
                    except Exception:
                        continue

        # Sort by most urgent (fewest days left)
        suggestions.sort(key=lambda x: x['days_left'])
        return jsonify({"success": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@ai_bp.route('/api/scan_invoice', methods=['POST'])
@ai_bp.route('/scan-invoice', methods=['POST'])
def scan_invoice_api():
    return jsonify({"success": True, "message": "OCR scanning is a premium feature. Please upgrade your plan.", "items": []})


@ai_bp.route('/api/generate_promo', methods=['POST'])
def generate_promo_api():
    return jsonify({"success": True, "promo": "Special Offer! Get 10% off on all items today at our store! \U0001f3ea\u2728"})
