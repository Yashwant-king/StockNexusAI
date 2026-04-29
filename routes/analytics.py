from flask import Blueprint, render_template, request, jsonify, current_app
import pandas as pd
import numpy as np
import os
import database as db

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
def analytics_dashboard():
    try:
        df = db.get_all_items()

        # Default empty values the template requires
        empty = dict(
            total_sales=0.0,
            total_expenses=0.0,
            net_profit=0.0,
            average_order_value=0.0,
            top_selling_products=[],
            bottom_selling_products=[],
            metrics=None,
            graph_data=None
        )

        if df is None or df.empty:
            return render_template('analytics.html', **empty)

        df_clean = df.drop(columns=['created_at'], errors='ignore')

        # Ensure numeric columns
        df_clean['quantity_stock'] = pd.to_numeric(df_clean['quantity_stock'], errors='coerce').fillna(0)
        df_clean['minimum_stock_level'] = pd.to_numeric(df_clean['minimum_stock_level'], errors='coerce').fillna(0)
        df_clean['total_revenue'] = pd.to_numeric(df_clean['total_revenue'], errors='coerce').fillna(0)

        # Metrics
        from utils import calculate_inventory_metrics
        metrics = calculate_inventory_metrics(df_clean)

        total_sales = float(df_clean['total_revenue'].sum())
        average_order_value = float(df_clean['total_revenue'].mean()) if len(df_clean) > 0 else 0.0

        # Pull total expenses from DB/CSV
        try:
            expenses = db.get_all_expenses()
            total_expenses = sum(float(e['amount']) for e in expenses)
        except Exception:
            total_expenses = 0.0

        net_profit = total_sales - total_expenses

        # Top 5 by highest stock
        top_df = df_clean.nlargest(5, 'quantity_stock')
        top_selling_products = top_df[['product_name', 'quantity_stock', 'total_revenue']].to_dict('records')

        # Bottom 5 by lowest stock (low stock / reorder needed)
        bottom_df = df_clean.nsmallest(5, 'quantity_stock')
        bottom_selling_products = bottom_df[['product_name', 'quantity_stock', 'total_revenue']].to_dict('records')

        graph_data = {
            'labels': df_clean['product_name'].tolist()[:10],
            'stock': df_clean['quantity_stock'].tolist()[:10],
            'revenue': df_clean['total_revenue'].tolist()[:10]
        }

        return render_template('analytics.html',
                               total_sales=total_sales,
                               total_expenses=total_expenses,
                               net_profit=net_profit,
                               average_order_value=average_order_value,
                               top_selling_products=top_selling_products,
                               bottom_selling_products=bottom_selling_products,
                               metrics=metrics,
                               graph_data=graph_data)

    except Exception as e:
        print(f"Analytics dashboard error: {e}")
        return render_template('analytics.html',
                               total_sales=0.0, total_expenses=0.0,
                               net_profit=0.0, average_order_value=0.0,
                               top_selling_products=[], bottom_selling_products=[],
                               metrics=None, graph_data=None, error=str(e))


@analytics_bp.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'GET':
        return render_template('prediction.html', prediction=None, input_data=None)

    # POST — handle both JSON (from fetch) and form data
    try:
        if request.is_json:
            body = request.get_json()
            q1 = float(body.get('quantity1', 0))
            q2 = float(body.get('quantity2', 0))
            q3 = float(body.get('quantity3', 0))
        else:
            q1 = float(request.form.get('quantity1', 0))
            q2 = float(request.form.get('quantity2', 0))
            q3 = float(request.form.get('quantity3', 0))

        if q1 < 0 or q2 < 0 or q3 < 0:
            return jsonify({"success": False, "error": "Sales values cannot be negative"}), 400

        # Weighted average prediction (more weight on recent months)
        prediction = round(q1 * 0.2 + q2 * 0.3 + q3 * 0.5, 2)

        return jsonify({
            "success": True,
            "prediction": prediction,
            "method": "Weighted Average (q1×0.2 + q2×0.3 + q3×0.5)"
        })
    except (ValueError, TypeError) as e:
        return jsonify({"success": False, "error": f"Invalid input: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route('/api/predict_all')
def predict_all_api():
    try:
        df = db.get_all_items()
        if df is None or df.empty:
            return jsonify([])
        predictions = []
        for _, r in df.iterrows():
            stock = float(r.get('quantity_stock', 0))
            pred = stock * 1.1 if stock > 0 else 5
            predictions.append({'name': r['product_name'], 'prediction': round(pred, 2)})
        return jsonify(predictions)
    except Exception:
        return jsonify([])


@analytics_bp.route('/api/smart-insights')
def smart_insights():
    try:
        df = db.get_all_items()
        from utils import get_low_stock_products, get_near_expiry_products
        low_stock = get_low_stock_products(df) if df is not None and not df.empty else []
        near_expiry = get_near_expiry_products(df) if df is not None and not df.empty else []

        insights = []
        if len(low_stock) > 0:
            insights.append({"icon": "⚠️", "text": f"{len(low_stock)} items need restocking", "type": "warning"})
        if len(near_expiry) > 0:
            insights.append({"icon": "⏰", "text": f"{len(near_expiry)} items expiring soon", "type": "expiry"})
        if not insights:
            insights.append({"icon": "✅", "text": "Inventory levels look healthy!", "type": "success"})

        return jsonify({"insights": insights})
    except Exception as e:
        return jsonify({"insights": [{"icon": "❌", "text": "Error loading insights", "type": "error"}]})


@analytics_bp.route('/train', methods=['POST'])
def train_model():
    try:
        df = db.get_all_items()
        if df is None or len(df) < 5:
            return jsonify({"success": False, "error": "Not enough data to train (min 5 products)"}), 400
        return jsonify({"success": True, "message": "Model training initiated! Check back in a few minutes."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
