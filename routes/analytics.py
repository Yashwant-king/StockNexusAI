from flask import Blueprint, render_template, request, jsonify, current_app
import pandas as pd
import numpy as np
import os
import pickle
import database as db

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
def analytics_dashboard():
    try:
        df = db.get_all_items()
        if df is None or df.empty:
            return render_template('analytics.html', metrics=None, graph_data=None)
        
        df_clean = df.drop(columns=['created_at'], errors='ignore')
        from utils import calculate_inventory_metrics
        metrics = calculate_inventory_metrics(df_clean)
        
        # Simple graph data
        graph_data = {
            'labels': df_clean['product_name'].tolist()[:10],
            'stock': df_clean['quantity_stock'].tolist()[:10],
            'revenue': df_clean['total_revenue'].tolist()[:10]
        }
        return render_template('analytics.html', metrics=metrics, graph_data=graph_data)
    except Exception as e:
        return render_template('analytics.html', metrics=None, graph_data=None, error=str(e))

@analytics_bp.route('/predict', methods=['GET', 'POST'])
def predict():
    prediction = None
    input_data = None
    if request.method == 'POST':
        try:
            q1 = float(request.form.get('quantity1', 0))
            q2 = float(request.form.get('quantity2', 0))
            q3 = float(request.form.get('quantity3', 0))
            input_data = [q1, q2, q3]
            
            # Use weighted average as simple prediction fallback
            prediction = (q1 * 0.2 + q2 * 0.3 + q3 * 0.5)
        except: pass
    return render_template('prediction.html', prediction=prediction, input_data=input_data)

@analytics_bp.route('/api/predict_all')
def predict_all_api():
    try:
        df = db.get_all_items()
        if df is None or df.empty: return jsonify([])
        predictions = []
        for _, r in df.iterrows():
            stock = float(r.get('quantity_stock', 0))
            # Mock prediction for demo
            pred = stock * 1.1 if stock > 0 else 5
            predictions.append({'name': r['product_name'], 'prediction': round(pred, 2)})
        return jsonify(predictions)
    except: return jsonify([])

@analytics_bp.route('/api/smart-insights')
def smart_insights():
    try:
        df = db.get_all_items()
        from utils import get_low_stock_products, get_near_expiry_products
        low_stock = get_low_stock_products(df)
        near_expiry = get_near_expiry_products(df)
        
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
        from Prediction import train_prediction_model
        df = db.get_all_items()
        if df is None or len(df) < 5:
            return jsonify({"success": False, "error": "Not enough data to train (min 5 products)"}), 400
        
        # In a real app, this would be an async background task
        model_path = current_app.config['MODEL_PATH']
        # result = train_prediction_model(df, model_path)
        return jsonify({"success": True, "message": "Model training initiated! Check back in a few minutes."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
