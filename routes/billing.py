from flask import Blueprint, render_template, request, jsonify, current_app
import pandas as pd
import database as db
from datetime import datetime

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/dukaan')
def dukaan():
    """Public-facing Digital Dukaan page for customers"""
    try:
        df = db.get_all_items()
        products = []
        deals = []
        if df is not None and not df.empty:
            df = df.drop(columns=['created_at'], errors='ignore')
            df['quantity_stock'] = pd.to_numeric(df['quantity_stock'], errors='coerce').fillna(0)
            df['total_revenue'] = pd.to_numeric(df['total_revenue'], errors='coerce').fillna(0)
            for _, row in df.iterrows():
                products.append({
                    'name': row.get('product_name', ''),
                    'stock': int(row.get('quantity_stock', 0)),
                    'price': float(row.get('total_revenue', 0)),
                })
            today = datetime.now()
            for _, row in df.iterrows():
                try:
                    exp_str = str(row.get('expiry_date', ''))
                    for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            exp_date = datetime.strptime(exp_str, fmt)
                            days_left = (exp_date - today).days
                            if 0 < days_left <= 10 and int(row.get('quantity_stock', 0)) > 0:
                                discount = min(50, max(15, 55 - days_left * 5))
                                deals.append({
                                    'name': row.get('product_name', ''),
                                    'discount': discount,
                                    'days_left': days_left,
                                    'original': float(row.get('total_revenue', 0)),
                                })
                            break
                        except: continue
                except: continue
        return render_template('dukaan.html', products=products, deals=deals, total_products=len(products))
    except Exception as e:
        return render_template('dukaan.html', products=[], deals=[], total_products=0)

@billing_bp.route('/bill')
def billing_system():
    try:
        df = db.get_all_items()
        products = []
        if df is not None and not df.empty:
            df = df.drop(columns=['created_at'], errors='ignore')
            for _, r in df.iterrows():
                products.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'price': float(r.get('total_revenue', 0)),
                    'stock': int(pd.to_numeric(r.get('quantity_stock', 0), errors='coerce'))
                })
        return render_template('bill.html', products=products)
    except:
        return render_template('bill.html', products=[])

@billing_bp.route('/barcodes')
def barcodes_page():
    try:
        df = db.get_all_items()
        items = []
        if df is not None and not df.empty:
            for _, r in df.iterrows():
                items.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'price': float(r.get('total_revenue', 0))
                })
        return render_template('barcodes.html', items=items)
    except:
        return render_template('barcodes.html', items=[])

@billing_bp.route('/purchase-order')
def purchase_order():
    try:
        df = db.get_all_items()
        low_stock_items = []
        if df is not None and not df.empty:
            df['quantity_stock'] = pd.to_numeric(df['quantity_stock'], errors='coerce').fillna(0)
            df['minimum_stock_level'] = pd.to_numeric(df['minimum_stock_level'], errors='coerce').fillna(0)
            low = df[df['quantity_stock'] <= df['minimum_stock_level']]
            for _, r in low.iterrows():
                stock = int(r.get('quantity_stock', 0))
                min_stock = int(r.get('minimum_stock_level', 0))
                suggested_qty = max(min_stock * 2 - stock, 10)
                low_stock_items.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'stock': stock,
                    'min_level': min_stock,
                    'reorder_qty': suggested_qty
                })
        return render_template('po.html', items=low_stock_items)
    except:
        return render_template('po.html', items=[])

@billing_bp.route('/api/checkout', methods=['POST'])
def POS_checkout():
    try:
        data = request.get_json()
        cart = data.get('cart', {})
        customer_phone = data.get('customer_phone', '').strip()
        points_to_redeem = int(data.get('points_redeemed', 0))
        if not cart:
            return jsonify({"success": False, "error": "Cart is empty"}), 400
        total_bill = 0
        for product_id, item in cart.items():
            total_bill += int(item['qty']) * float(item['price'])
        final_bill = total_bill - points_to_redeem
        points_earned = int(final_bill // 100)

        if db.use_db():
            conn = db.get_connection()
            try:
                cur = conn.cursor(cursor_factory=db.RealDictCursor)
                for pid, item in cart.items():
                    qty, price = int(item['qty']), float(item['price'])
                    cur.execute("UPDATE inventory SET quantity_stock=quantity_stock-%s, total_revenue=total_revenue+%s WHERE id=%s OR product_id=%s;", (qty, qty*price, pid, pid))
                if customer_phone:
                    cur.execute("SELECT id, loyalty_points FROM khata_customers WHERE phone=%s;", (customer_phone,))
                    row = cur.fetchone()
                    if row:
                        new_pts = int(row['loyalty_points'] or 0) - points_to_redeem + points_earned
                        cur.execute("UPDATE khata_customers SET loyalty_points=%s WHERE id=%s;", (new_pts, row['id']))
                    else:
                        cur.execute("INSERT INTO khata_customers (name, phone, loyalty_points) VALUES (%s,%s,%s);", ("Customer "+customer_phone[-4:], customer_phone, points_earned))
                conn.commit()
            finally: db.release_connection(conn)
        else:
            csv_path = current_app.config['DATA_PATH']
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                for pid, item in cart.items():
                    mask = df['product_id'].astype(str) == str(pid)
                    if mask.any():
                        df.loc[mask, 'quantity_stock'] = df.loc[mask, 'quantity_stock'].astype(int) - int(item['qty'])
                        df.loc[mask, 'total_revenue'] = df.loc[mask, 'total_revenue'].astype(float) + (int(item['qty']) * float(item['price']))
                df.to_csv(csv_path, index=False)
        return jsonify({"success": True, "points_earned": points_earned, "final_bill": final_bill})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@billing_bp.route('/api/loyalty', methods=['POST'])
def check_loyalty():
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        if not phone: return jsonify({"success": False, "points": 0})
        if db.use_db():
            conn = db.get_connection()
            try:
                cur = conn.cursor(cursor_factory=db.RealDictCursor)
                cur.execute("SELECT loyalty_points, name FROM khata_customers WHERE phone=%s;", (phone,))
                row = cur.fetchone()
                if row: return jsonify({"success": True, "points": int(row['loyalty_points'] or 0), "name": str(row['name'])})
                return jsonify({"success": False, "points": 0, "message": "Not found"})
            finally: db.release_connection(conn)
        return jsonify({"success": False, "points": 0, "message": "DB required"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
