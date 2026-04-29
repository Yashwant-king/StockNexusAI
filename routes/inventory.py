from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, send_file
import pandas as pd
import os
import io
from datetime import datetime
import database as db
from utils import get_low_stock_products, get_near_expiry_products, calculate_inventory_metrics

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/dashboard')
def home():
    df = db.get_all_items()
    all_items = []
    if df is not None and not df.empty:
        df = df.drop(columns=['created_at'], errors='ignore')
        for _, row in df.iterrows():
            all_items.append({
                'product_id': row.get('product_id', ''),
                'product_name': row.get('product_name', ''),
                'quantity_stock': row.get('quantity_stock', 0),
                'minimum_stock_level': row.get('minimum_stock_level', 0),
                'total_revenue': row.get('total_revenue', 0),
                'expiry_date': row.get('expiry_date', ''),
            })
        all_items.reverse()
    return render_template("index.html", all_items=all_items)

@inventory_bp.route('/inventory')
def inventory():
    """Display inventory with restocking and expiry recommendations"""
    try:
        df = db.get_all_items()
        if df is None or df.empty:
            return render_template('inventory.html',
                                 restock_recommendations=[],
                                 near_expiry_recommendations=[],
                                 metrics=None,
                                 all_items=[])

        df_for_report = df.drop(columns=['created_at'], errors='ignore')
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        df_for_report.to_csv(current_app.config['DATA_PATH'], index=False)

        low_stock_recommendations = get_low_stock_products(df_for_report)
        near_expiry_recommendations = get_near_expiry_products(df_for_report)
        metrics = calculate_inventory_metrics(df_for_report)

        all_items = []
        for _, row in df_for_report.iterrows():
            all_items.append({
                'product_id': row.get('product_id', ''),
                'product_name': row.get('product_name', ''),
                'quantity_stock': row.get('quantity_stock', 0),
                'minimum_stock_level': row.get('minimum_stock_level', 0),
                'total_revenue': row.get('total_revenue', 0),
                'expiry_date': row.get('expiry_date', ''),
            })

        return render_template('inventory.html',
                             restock_recommendations=low_stock_recommendations,
                             near_expiry_recommendations=near_expiry_recommendations,
                             metrics=metrics,
                             all_items=all_items)
    except Exception as e:
        print(f"Inventory page error: {e}")
        return render_template('inventory.html',
                             restock_recommendations=[],
                             near_expiry_recommendations=[],
                             metrics=None,
                             all_items=[],
                             error=str(e))

@inventory_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with improved error handling"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No selected file"}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({"success": False, "error": "Please upload a CSV file"}), 400
        
        content = file.read()
        df_upload = pd.read_csv(io.BytesIO(content))
        success = db.bulk_upload_from_df(df_upload)
        
        if success:
            return jsonify({"success": True, "message": f"Successfully uploaded {len(df_upload)} items!"}), 200
        return jsonify({"success": False, "error": "Failed to save data."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_bp.route('/add_item', methods=['POST'])
def add_item():
    try:
        data = request.form
        success = db.add_item(
            product_id=str(data.get('itemId', '')).strip(),
            product_name=str(data.get('itemName', '')).strip(),
            quantity_stock=int(data.get('itemStock', 0)),
            minimum_stock_level=int(data.get('itemMinStock', 0)),
            total_revenue=float(data.get('itemRevenue', 0)),
            expiry_date=str(data.get('itemExpiry', '')).strip()
        )
        if success:
            return jsonify({"success": True, "message": f"Added {data.get('itemName')}!"}), 200
        return jsonify({"success": False, "error": "Failed to add item."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_bp.route('/api/delete_item', methods=['POST'])
def delete_item():
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        if not item_id:
             return jsonify({"success": False, "error": "No ID provided"}), 400
        
        # Note: database.py delete_item uses DB ID if in DB mode, 
        # or product_id if in CSV mode (though current implementation is limited)
        # We need to handle this carefully.
        success = db.delete_item(item_id)
        if success:
            return jsonify({"success": True, "message": "Item deleted!"}), 200
        return jsonify({"success": False, "error": "Failed to delete."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_bp.route('/api/export-csv')
def export_csv():
    try:
        df = db.get_all_items()
        if df is not None and not df.empty:
            df = df.drop(columns=['created_at'], errors='ignore')
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            mem = io.BytesIO()
            mem.write(output.getvalue().encode('utf-8'))
            mem.seek(0)
            return send_file(mem, mimetype='text/csv', as_attachment=True,
                           download_name='stocknexus_inventory.csv')
        return jsonify({'error': 'No data'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventory_bp.route('/api/notifications')
def get_notifications():
    try:
        alerts = []
        df = db.get_all_items()
        if df is not None and not df.empty:
            df['quantity_stock'] = pd.to_numeric(df['quantity_stock'], errors='coerce').fillna(0)
            df['minimum_stock_level'] = pd.to_numeric(df['minimum_stock_level'], errors='coerce').fillna(0)
            
            low = df[df['quantity_stock'] <= df['minimum_stock_level']]
            for _, r in low.iterrows():
                alerts.append({'icon': '⚠️', 'text': f"{r['product_name']} is low", 'type': 'warning'})
            
            today = datetime.now()
            for _, r in df.iterrows():
                try:
                    for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            exp = datetime.strptime(str(r.get('expiry_date', '')), fmt)
                            days = (exp - today).days
                            if 0 <= days <= 5:
                                alerts.append({'icon': '⏰', 'text': f"{r['product_name']} expires in {days}d", 'type': 'expiry'})
                            elif days < 0:
                                alerts.append({'icon': '🚨', 'text': f"{r['product_name']} EXPIRED!", 'type': 'danger'})
                            break
                        except: continue
                except: continue
        
        try:
            customers = db.get_all_customers()
            overdue = [c for c in customers if c.get('balance', 0) > 0]
            if overdue:
                alerts.append({'icon': '📒', 'text': f"{len(overdue)} customers pending", 'type': 'khata'})
        except: pass
        
        return jsonify({'count': len(alerts), 'alerts': alerts[:10]})
    except Exception as e:
        return jsonify({'count': 0, 'alerts': [], 'error': str(e)})
