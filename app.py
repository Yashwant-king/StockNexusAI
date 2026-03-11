from flask import Flask, request, render_template, jsonify
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt
import os
import warnings
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from utils import generate_inventory_report, get_low_stock_products, get_near_expiry_products
import database as db

# Suppress TensorFlow warnings
warnings.filterwarnings('ignore', category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'data_set'
app.config['MODEL_PATH'] = 'trained_model.pkl'
app.config['DATA_PATH'] = 'data_set/data.csv'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Load the pickled model
def load_trained_model():
    """Load the trained model with proper error handling"""
    try:
        with open(app.config['MODEL_PATH'], 'rb') as model_file:
            model_data = pickle.load(model_file)
        
        # Check if the loaded data is a model or a dictionary containing a model
        if hasattr(model_data, 'predict'):
            print("Model loaded successfully!")
            return model_data
        elif isinstance(model_data, dict) and 'model' in model_data:
            print("Model loaded successfully from dictionary!")
            return model_data['model']
        else:
            print("Loaded data is not a valid model")
            return None
    except FileNotFoundError:
        print(f"Model file not found at {app.config['MODEL_PATH']}")
        return None
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        return None

def simple_prediction(quantity1, quantity2, quantity3):
    """Simple prediction using weighted average"""
    try:
        # Simple weighted average prediction
        weights = [0.2, 0.3, 0.5]  # Give more weight to recent data
        prediction = (quantity1 * weights[0] + quantity2 * weights[1] + quantity3 * weights[2])
        return prediction
    except Exception as e:
        print(f"Simple prediction error: {str(e)}")
        return None

model = load_trained_model()

# Initialize the database (create tables if needed)
with __import__('contextlib').suppress(Exception):
    db.init_db()
    db.init_khata_db()

@app.route('/')
def login_page():
    return render_template("login.html")

@app.route('/dashboard')
def home():
    return render_template("index.html")

@app.route('/dukaan')
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

            # Build product list
            for _, row in df.iterrows():
                products.append({
                    'name': row.get('product_name', ''),
                    'stock': int(row.get('quantity_stock', 0)),
                    'price': float(row.get('total_revenue', 0)),
                })

            # Auto-generate deals from near-expiry items
            from datetime import datetime
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
                        except:
                            continue
                except:
                    continue

        return render_template('dukaan.html',
                             products=products,
                             deals=deals,
                             total_products=len(products))
    except Exception as e:
        print(f"Dukaan error: {e}")
        return render_template('dukaan.html', products=[], deals=[], total_products=0)

@app.route('/bill')
def bill_page():
    try:
        df = db.get_all_items()
        products = []
        if df is not None and not df.empty:
            df = df.drop(columns=['created_at'], errors='ignore')
            for _, r in df.iterrows():
                products.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'price': float(r.get('total_revenue', 0)), # Using revenue acting as price for now
                    'stock': int(pd.to_numeric(r.get('quantity_stock', 0), errors='coerce'))
                })
        return render_template('bill.html', products=products)
    except:
        return render_template('bill.html', products=[])

@app.route('/barcodes')
def barcodes_page():
    """Page to print barcodes for all inventory items"""
    try:
        df = db.get_all_items()
        items = []
        if df is not None and not df.empty:
            df = df.drop(columns=['created_at'], errors='ignore')
            for _, r in df.iterrows():
                items.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'price': float(r.get('total_revenue', 0))
                })
        return render_template('barcodes.html', items=items)
    except Exception as e:
        print(f"Barcode error: {e}")
        return render_template('barcodes.html', items=[])

@app.route('/purchase-order')
def purchase_order_page():
    """Auto-generate a PO for low stock items"""
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
                # Suggest reordering enough to be twice the minimum stock level
                suggested_qty = max(min_stock * 2 - stock, 10)
                
                low_stock_items.append({
                    'id': str(r.get('product_id', '')),
                    'name': str(r.get('product_name', '')),
                    'stock': stock,
                    'min_level': min_stock,
                    'reorder_qty': suggested_qty
                })
        return render_template('po.html', items=low_stock_items)
    except Exception as e:
        print(f"PO error: {e}")
        return render_template('po.html', items=[])

@app.route('/api/export-csv')
def export_csv():
    """Download inventory as CSV file"""
    try:
        from flask import send_file
        import io
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

@app.route('/api/notifications')
def get_notifications():
    """Get alert notifications for navbar bell"""
    try:
        alerts = []
        df = db.get_all_items()
        if df is not None and not df.empty:
            df['quantity_stock'] = pd.to_numeric(df['quantity_stock'], errors='coerce').fillna(0)
            df['minimum_stock_level'] = pd.to_numeric(df['minimum_stock_level'], errors='coerce').fillna(0)
            # Low stock alerts
            low = df[df['quantity_stock'] <= df['minimum_stock_level']]
            for _, r in low.iterrows():
                alerts.append({'icon': '⚠️', 'text': f"{r['product_name']} is low ({int(r['quantity_stock'])} left)", 'type': 'warning'})
            # Near expiry
            from datetime import datetime
            today = datetime.now()
            for _, r in df.iterrows():
                try:
                    for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            exp = datetime.strptime(str(r.get('expiry_date', '')), fmt)
                            days = (exp - today).days
                            if days <= 5 and days >= 0:
                                alerts.append({'icon': '⏰', 'text': f"{r['product_name']} expires in {days}d", 'type': 'expiry'})
                            elif days < 0:
                                alerts.append({'icon': '🚨', 'text': f"{r['product_name']} EXPIRED!", 'type': 'danger'})
                            break
                        except: continue
                except: continue
        # Khata alerts
        try:
            customers = db.get_all_customers()
            overdue = [c for c in customers if c.get('balance', 0) > 0]
            if overdue:
                alerts.append({'icon': '📒', 'text': f"{len(overdue)} customers have pending payments", 'type': 'khata'})
        except: pass
        return jsonify({'count': len(alerts), 'alerts': alerts[:10]})
    except Exception as e:
        return jsonify({'count': 0, 'alerts': [], 'error': str(e)})

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with improved error handling"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file part"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No selected file"
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                "success": False,
                "error": "Please upload a CSV file"
            }), 400
        
        # Save to database (or CSV fallback)
        import io
        content = file.read()
        df_upload = pd.read_csv(io.BytesIO(content))
        success = db.bulk_upload_from_df(df_upload)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Successfully uploaded {len(df_upload)} items to inventory!"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save data. Please try again."
            }), 500
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error saving file: {str(e)}"
        }), 500

@app.route('/add_item', methods=['POST'])
def add_item():
    """Handle adding a single item directly to the database"""
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
            return jsonify({
                "success": True,
                "message": f"Successfully added {data.get('itemName')} to inventory!"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to add item to database."
            }), 500

    except Exception as e:
        print(f"Add item error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error adding item: {str(e)}"
        }), 500

@app.route('/inventory')
def inventory():
    """Display inventory with restocking and expiry recommendations"""
    try:
        # Get data from database (or CSV fallback)
        df = db.get_all_items()

        if df is None or df.empty:
            return render_template('inventory.html',
                                 restock_recommendations=[],
                                 near_expiry_recommendations=[],
                                 metrics=None,
                                 all_items=[])

        # Save to CSV for compatibility with utils
        df_for_report = df.drop(columns=['created_at'], errors='ignore')
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        df_for_report.to_csv(app.config['DATA_PATH'], index=False)

        # Get recommendations
        low_stock_recommendations = get_low_stock_products(df_for_report)
        near_expiry_recommendations = get_near_expiry_products(df_for_report)

        # Get inventory metrics
        from utils import calculate_inventory_metrics
        metrics = calculate_inventory_metrics(df_for_report)

        # Build all_items list for the full table
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

@app.route('/api/delete_item', methods=['POST'])
def api_delete_item():
    """Delete an item by product_id"""
    try:
        data = request.get_json()
        product_id = str(data.get('product_id', '')).strip()
        if not product_id:
            return jsonify({"success": False, "error": "No product_id provided"}), 400

        deleted = False

        # Try deleting from database
        if db.use_db():
            try:
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM inventory WHERE product_id = %s;", (product_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                cur.close()
                conn.close()
                if deleted:
                    print(f"✅ Deleted product {product_id} from DB")
            except Exception as e:
                print(f"❌ DB delete error: {e}")

        # Also delete from CSV (fallback / sync)
        csv_path = app.config['DATA_PATH']
        if os.path.exists(csv_path):
            try:
                csv_df = pd.read_csv(csv_path)
                before_count = len(csv_df)
                csv_df = csv_df[csv_df['product_id'].astype(str) != product_id]
                if len(csv_df) < before_count:
                    csv_df.to_csv(csv_path, index=False)
                    deleted = True
                    print(f"✅ Deleted product {product_id} from CSV")
            except Exception as e:
                print(f"❌ CSV delete error: {e}")

        if deleted:
            return jsonify({"success": True, "message": f"Product {product_id} deleted!"})
        else:
            return jsonify({"success": False, "error": "Product not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/predict', methods=["GET", "POST"])
def predict():
    """Handle prediction requests with improved error handling"""
    if request.method == "POST":
        try:
            # Extract input data from the request
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "error": "No data provided"
                }), 400
            
            quantity1 = float(data.get('quantity1', 0))
            quantity2 = float(data.get('quantity2', 0))
            quantity3 = float(data.get('quantity3', 0))

            # Validate input data
            if quantity1 < 0 or quantity2 < 0 or quantity3 < 0:
                return jsonify({
                    "success": False,
                    "error": "Quantities must be non-negative"
                }), 400

            # Try to use the trained model first
            if model is not None and hasattr(model, 'predict'):
                try:
                    # Prepare the input data for prediction
                    input_data = np.array([[quantity1, quantity2, quantity3]])
                    prediction_value = model.predict(input_data)[0][0]
                    return jsonify({
                        "success": True,
                        "prediction": float(prediction_value)
                    })
                except Exception as model_error:
                    print(f"Model prediction failed: {str(model_error)}")
                    # Fall back to simple prediction
                    pass

            # Fallback to simple prediction
            prediction_value = simple_prediction(quantity1, quantity2, quantity3)
            if prediction_value is not None:
                return jsonify({
                    "success": True,
                    "prediction": float(prediction_value),
                    "method": "simple_weighted_average"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to make prediction"
                }), 500

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid input data: {str(e)}"
            }), 400
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Failed to make prediction: {str(e)}"
            }), 500

    elif request.method == "GET":
        return render_template("prediction.html")

@app.route('/analytics')
def sales_analytics():
    """Display sales analytics with improved error handling"""
    try:
        # Get data from database (or CSV fallback)
        data = db.get_all_items()

        if data is None or data.empty:
            return render_template('error.html',
                                 error="No inventory data found. Please upload a CSV or add items first.")

        data = data.drop(columns=['created_at'], errors='ignore')

        # Convert columns to numeric to prevent dtype errors
        data['quantity_stock'] = pd.to_numeric(data['quantity_stock'], errors='coerce').fillna(0).astype(int)
        data['total_revenue'] = pd.to_numeric(data['total_revenue'], errors='coerce').fillna(0).astype(float)
        data['minimum_stock_level'] = pd.to_numeric(data['minimum_stock_level'], errors='coerce').fillna(0).astype(int)

        # Calculate total sales and average order value
        total_sales = float(data["total_revenue"].sum())
        average_order_value = float(data["total_revenue"].mean())

        # Find top 5 and bottom 5 products
        top_selling_products = data.nlargest(5, "quantity_stock")
        bottom_selling_products = data.nsmallest(5, "quantity_stock")

        # Convert DataFrames to dictionaries and ensure JSON serializable
        top_selling_dict = []
        for _, row in top_selling_products.iterrows():
            try:
                pid = int(row['product_id'])
            except (ValueError, TypeError):
                pid = 0
            top_selling_dict.append({
                'product_id': pid,
                'product_name': str(row['product_name']),
                'quantity_stock': int(row['quantity_stock']),
                'total_revenue': float(row['total_revenue'])
            })

        bottom_selling_dict = []
        for _, row in bottom_selling_products.iterrows():
            try:
                pid = int(row['product_id'])
            except (ValueError, TypeError):
                pid = 0
            bottom_selling_dict.append({
                'product_id': pid,
                'product_name': str(row['product_name']),
                'quantity_stock': int(row['quantity_stock']),
                'total_revenue': float(row['total_revenue'])
            })

        # Create sales trend plot
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(range(len(data)), data['total_revenue'], marker='o', linestyle='-', linewidth=2, markersize=4)
            ax.set_title('Revenue Trend by Product', fontsize=16, fontweight='bold')
            ax.set_xlabel('Product Index', fontsize=12)
            ax.set_ylabel('Total Revenue', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#f8f9fa')
            fig.patch.set_facecolor('white')
            fig.tight_layout()

            # Save the plot to a static file
            sales_trend_file_path = "static/sales_trend.png"
            fig.savefig(sales_trend_file_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
        except Exception as e:
            print(f"Error creating sales trend plot: {e}")

        return render_template('analytics.html', 
                             total_sales=total_sales,
                             average_order_value=average_order_value,
                             top_selling_products=top_selling_dict,
                             bottom_selling_products=bottom_selling_dict)
    except Exception as e:
        print(f"Analytics error: {str(e)}")
        return render_template('error.html', error=f"Error loading analytics: {str(e)}")

@app.route('/train', methods=['POST'])
def train_model():
    """Train the prediction model"""
    try:
        from Prediction import main as train_prediction_model
        print("Starting model training process...")
        success = train_prediction_model()
        
        if success:
            # Reload the model
            global model
            model = load_trained_model()
            if model is not None:
                return jsonify({
                    "success": True,
                    "message": "Model trained successfully!"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": "Model training completed but failed to load the model."
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": "Model training failed. Check the logs for details."
            }), 500
    except Exception as e:
        print(f"Training error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error training model: {str(e)}"
        }), 500

@app.route('/api/smart-insights')
def smart_insights():
    """ML-powered insights: ABC Analysis, Expiry Alerts, Anomaly Detection"""
    try:
        df = db.get_all_items()
        insights = []

        if df is None or df.empty:
            return jsonify({"insights": [{"icon": "📦", "text": "Add products to get AI-powered insights!", "type": "info"}]})

        df_clean = df.drop(columns=['created_at'], errors='ignore')

        # ── 1. ABC ANALYSIS (Revenue Pareto) ──
        try:
            df_sorted = df_clean.sort_values('total_revenue', ascending=False)
            total_rev = df_sorted['total_revenue'].astype(float).sum()
            if total_rev > 0:
                df_sorted['cum_pct'] = df_sorted['total_revenue'].astype(float).cumsum() / total_rev * 100
                a_items = df_sorted[df_sorted['cum_pct'] <= 80]
                b_items = df_sorted[(df_sorted['cum_pct'] > 80) & (df_sorted['cum_pct'] <= 95)]
                c_items = df_sorted[df_sorted['cum_pct'] > 95]
                top = df_sorted.iloc[0]
                insights.append({
                    "icon": "🏆", "type": "abc",
                    "text": f"ABC Analysis: {len(a_items)} products generate 80% of your ₹{total_rev:,.0f} revenue. Top earner: {top['product_name']} (₹{float(top['total_revenue']):,.0f})"
                })
                if len(c_items) > 0:
                    c_names = ', '.join(c_items['product_name'].head(3).tolist())
                    insights.append({
                        "icon": "📉", "type": "abc",
                        "text": f"Low Performers (C-grade): {c_names} — consider reducing stock or replacing with better-selling items"
                    })
        except Exception as e:
            print(f"ABC error: {e}")

        # ── 2. SMART EXPIRY ALERTS ──
        try:
            from datetime import datetime, timedelta
            today = datetime.now()
            for _, row in df_clean.iterrows():
                try:
                    exp_str = str(row.get('expiry_date', ''))
                    exp_date = None
                    for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            exp_date = datetime.strptime(exp_str, fmt)
                            break
                        except:
                            continue
                    if exp_date:
                        days_left = (exp_date - today).days
                        stock = int(row.get('quantity_stock', 0))
                        rev = float(row.get('total_revenue', 0))
                        if 0 < days_left <= 7 and stock > 0:
                            discount = min(50, max(20, 60 - days_left * 8))
                            potential_loss = rev * 0.3
                            insights.append({
                                "icon": "⏰", "type": "expiry",
                                "text": f"Sell {row['product_name']} at {discount}% discount ({days_left}d left). Save ~₹{potential_loss:,.0f} vs throwing away"
                            })
                        elif days_left <= 0 and stock > 0:
                            insights.append({
                                "icon": "🚨", "type": "expiry",
                                "text": f"{row['product_name']} has EXPIRED with {stock} units still in stock! Remove immediately"
                            })
                except:
                    continue
        except Exception as e:
            print(f"Expiry alert error: {e}")

        # ── 3. ANOMALY DETECTION (IQR method) ──
        try:
            df_clean['stock_f'] = df_clean['quantity_stock'].astype(float)
            df_clean['rev_f'] = df_clean['total_revenue'].astype(float)
            if len(df_clean) >= 4:
                # Stock anomalies
                q1 = df_clean['stock_f'].quantile(0.25)
                q3 = df_clean['stock_f'].quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    outliers = df_clean[(df_clean['stock_f'] < q1 - 1.5*iqr) | (df_clean['stock_f'] > q3 + 1.5*iqr)]
                    for _, row in outliers.iterrows():
                        stock = int(row['stock_f'])
                        if stock > q3 + 1.5*iqr:
                            insights.append({
                                "icon": "📊", "type": "anomaly",
                                "text": f"Anomaly: {row['product_name']} has unusually HIGH stock ({stock} units) — possible overstocking"
                            })
                        else:
                            insights.append({
                                "icon": "📊", "type": "anomaly",
                                "text": f"Anomaly: {row['product_name']} has unusually LOW stock ({stock} units) — restock urgently"
                            })
        except Exception as e:
            print(f"Anomaly detection error: {e}")

        # Low stock general alert
        try:
            low = df_clean[df_clean['quantity_stock'].astype(float) <= df_clean['minimum_stock_level'].astype(float)]
            if len(low) > 0:
                names = ', '.join(low['product_name'].head(4).tolist())
                insights.append({
                    "icon": "⚠️", "type": "lowstock",
                    "text": f"{len(low)} items below minimum stock: {names}"
                })
        except:
            pass

        # ── 4. PROFIT MARGIN ESTIMATOR ──
        try:
            total_rev = df_clean['total_revenue'].astype(float).sum()
            if total_rev > 0:
                estimated_cost = total_rev * 0.72  # Industry avg: 72% cost for kirana
                estimated_profit = total_rev - estimated_cost
                margin_pct = (estimated_profit / total_rev) * 100
                insights.append({
                    "icon": "💰", "type": "profit",
                    "text": f"Estimated Profit: ₹{estimated_profit:,.0f} ({margin_pct:.0f}% margin) from ₹{total_rev:,.0f} total revenue"
                })
        except:
            pass

        # ── 5. STOCK HEALTH SCORE ──
        try:
            total = len(df_clean)
            if total > 0:
                healthy = len(df_clean[df_clean['quantity_stock'].astype(float) > df_clean['minimum_stock_level'].astype(float)])
                score = int((healthy / total) * 100)
                emoji = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
                insights.append({
                    "icon": emoji, "type": "health",
                    "text": f"Stock Health Score: {score}% — {healthy}/{total} products are above minimum level"
                })
        except:
            pass

        # ── 6. TOP & BOTTOM PRODUCTS ──
        try:
            if len(df_clean) >= 3:
                top3 = df_clean.nlargest(3, 'total_revenue')
                top_names = ', '.join([f"{r['product_name']} (₹{float(r['total_revenue']):,.0f})" for _, r in top3.iterrows()])
                insights.append({
                    "icon": "🥇", "type": "ranking",
                    "text": f"Top Earners: {top_names}"
                })
                bottom = df_clean.nsmallest(1, 'total_revenue').iloc[0]
                insights.append({
                    "icon": "🐌", "type": "ranking",
                    "text": f"Slowest Product: {bottom['product_name']} (₹{float(bottom['total_revenue']):,.0f}) — consider replacing or promoting"
                })
        except:
            pass

        # ── 7. KHATA PAYMENT REMINDERS ──
        try:
            customers = db.get_all_customers()
            overdue = [c for c in customers if c['balance'] > 0]
            if overdue:
                total_due = sum(c['balance'] for c in overdue)
                top_debtor = max(overdue, key=lambda c: c['balance'])
                insights.append({
                    "icon": "📒", "type": "khata",
                    "text": f"Khata Alert: {len(overdue)} customers owe ₹{total_due:,.0f}. Biggest: {top_debtor['name']} (₹{top_debtor['balance']:,.0f})"
                })
        except:
            pass

        # ── 8. AUTO REORDER SUGGESTIONS ──
        try:
            for _, row in df_clean.iterrows():
                stock = float(row.get('quantity_stock', 0))
                min_level = float(row.get('minimum_stock_level', 0))
                name = row.get('product_name', '')
                if min_level > 0 and stock <= min_level * 1.2 and stock > 0:
                    # Estimate days until stockout (assuming ~10% daily usage of min_level)
                    daily_usage = max(min_level * 0.1, 1)
                    days_left = int(stock / daily_usage)
                    reorder_qty = int(min_level * 2 - stock)
                    insights.append({
                        "icon": "🔄", "type": "reorder",
                        "text": f"Reorder {name}: Only {int(stock)} left (~{days_left} days). Order {reorder_qty} units to be safe"
                    })
        except Exception as e:
            print(f"Reorder insight error: {e}")

        # ── 9. INVENTORY TURNOVER RATE ──
        try:
            if len(df_clean) >= 3:
                df_clean['turnover'] = df_clean['total_revenue'].astype(float) / (df_clean['quantity_stock'].astype(float).replace(0, 1))
                fast = df_clean[df_clean['turnover'] > df_clean['turnover'].quantile(0.75)]
                slow = df_clean[df_clean['turnover'] < df_clean['turnover'].quantile(0.25)]
                if len(fast) > 0:
                    fast_names = ', '.join(fast['product_name'].head(3).tolist())
                    insights.append({
                        "icon": "🚀", "type": "turnover",
                        "text": f"Fast-Moving Items: {fast_names} — high revenue per unit, always keep in stock!"
                    })
                if len(slow) > 0:
                    slow_names = ', '.join(slow['product_name'].head(3).tolist())
                    insights.append({
                        "icon": "🐢", "type": "turnover",
                        "text": f"Slow-Moving Items: {slow_names} — low turnover, consider discounting or replacing"
                    })
        except Exception as e:
            print(f"Turnover insight error: {e}")

        # ── 10. DEAD STOCK ALERT ──
        try:
            total_rev = df_clean['total_revenue'].astype(float).sum()
            if total_rev > 0 and len(df_clean) >= 3:
                avg_rev = total_rev / len(df_clean)
                dead = df_clean[df_clean['total_revenue'].astype(float) < avg_rev * 0.1]
                if len(dead) > 0:
                    dead_names = ', '.join(dead['product_name'].head(3).tolist())
                    dead_stock_val = dead['quantity_stock'].astype(float).sum()
                    insights.append({
                        "icon": "💀", "type": "dead",
                        "text": f"Dead Stock: {dead_names} — almost no revenue but holding {int(dead_stock_val)} units. Free up shelf space!"
                    })
        except Exception as e:
            print(f"Dead stock insight error: {e}")

        # ── 11. DAILY SALES SUMMARY ──
        try:
            total_rev = df_clean['total_revenue'].astype(float).sum()
            total_items = len(df_clean)
            total_stock = df_clean['quantity_stock'].astype(float).sum()
            if total_rev > 0:
                top_product = df_clean.loc[df_clean['total_revenue'].astype(float).idxmax()]
                insights.append({
                    "icon": "📊", "type": "summary",
                    "text": f"Inventory Summary: {total_items} products | {int(total_stock)} total units | ₹{total_rev:,.0f} revenue | Top: {top_product['product_name']}"
                })
        except Exception as e:
            print(f"Summary insight error: {e}")

        if not insights:
            insights.append({"icon": "✅", "text": "All systems healthy! No alerts right now.", "type": "info"})

        return jsonify({"insights": insights})
    except Exception as e:
        return jsonify({"insights": [{"icon": "❌", "text": f"Analysis error: {str(e)}", "type": "error"}]})

# ═══════════════════════════════════════════════
# KHATA (CREDIT BOOK) ROUTES
# ═══════════════════════════════════════════════

@app.route('/khata')
def khata_page():
    return render_template('khata.html')

@app.route('/api/khata/customers')
def get_khata_customers():
    try:
        customers = db.get_all_customers()
        total_outstanding = sum(c['balance'] for c in customers if c['balance'] > 0)
        return jsonify({
            'success': True,
            'customers': customers,
            'total_outstanding': total_outstanding,
            'total_customers': len(customers)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/khata/add-customer', methods=['POST'])
def add_khata_customer():
    try:
        data = request.get_json()
        name = str(data.get('name', '')).strip()
        phone = str(data.get('phone', '')).strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        new_id = db.add_customer(name, phone)
        if new_id:
            return jsonify({'success': True, 'message': f'{name} added!', 'id': new_id})
        return jsonify({'success': False, 'error': 'Failed to add customer'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/khata/add-transaction', methods=['POST'])
def add_khata_transaction():
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        txn_type = data.get('type', '')  # 'udhar' or 'payment'
        amount = float(data.get('amount', 0))
        note = str(data.get('note', '')).strip()
        if not customer_id or txn_type not in ['udhar', 'payment'] or amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400
        ok = db.add_transaction(customer_id, txn_type, amount, note)
        if ok:
            return jsonify({'success': True, 'message': f'₹{amount:.0f} {txn_type} recorded!'})
        return jsonify({'success': False, 'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/khata/transactions/<int:customer_id>')
def get_khata_transactions(customer_id):
    try:
        txns = db.get_customer_transactions(customer_id)
        return jsonify({'success': True, 'transactions': txns})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/khata/delete-customer', methods=['POST'])
def delete_khata_customer():
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        if db.delete_customer(customer_id):
            return jsonify({'success': True, 'message': 'Customer deleted'})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/inventory-summary')
def inventory_summary():
    """API endpoint for inventory summary"""
    try:
        # Get live data from database (or CSV fallback)
        df = db.get_all_items()
        last_updated = db.get_last_updated()

        if df is None or df.empty:
            return jsonify({
                "metrics": {
                    "total_products": 0,
                    "low_stock_count": 0,
                    "average_stock_level": 0,
                    "total_stock_value": 0,
                    "near_expiry_count": 0,
                    "total_revenue": 0,
                    "average_order_value": 0
                },
                "last_updated": None,
                "message": "No inventory data yet. Add your first product above!"
            }), 200

        # Save to CSV for compatibility with existing report generation
        df_for_report = df.drop(columns=['created_at'], errors='ignore')
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        df_for_report.to_csv(app.config['DATA_PATH'], index=False)

        report = generate_inventory_report(app.config['DATA_PATH'])

        if report:
            report['last_updated'] = last_updated
            return jsonify(report)
        else:
            return jsonify({
                "metrics": {
                    "total_products": len(df),
                    "low_stock_count": 0,
                    "average_stock_level": 0,
                    "total_stock_value": 0,
                    "near_expiry_count": 0,
                    "total_revenue": float(df['total_revenue'].sum()) if 'total_revenue' in df.columns else 0,
                    "average_order_value": 0
                },
                "last_updated": last_updated,
                "error": "Failed to generate detailed report"
            }), 200

    except Exception as e:
        print(f"Error in inventory summary: {str(e)}")
        return jsonify({
            "metrics": {
                "total_products": 0,
                "low_stock_count": 0,
                "average_stock_level": 0,
                "total_stock_value": 0,
                "near_expiry_count": 0,
                "total_revenue": 0,
                "average_order_value": 0
            },
            "last_updated": None,
            "error": str(e)
        }), 200

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    """AI Business Assistant powered by Groq LLaMA 3.3 70B"""
    try:
        from groq import Groq

        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({"success": False, "error": "No message provided"}), 400

        groq_api_key = os.environ.get('GROQ_API_KEY')
        if not groq_api_key:
            return jsonify({"success": False, "error": "AI Assistant not configured. Please set GROQ_API_KEY."}), 500

        # Get live inventory data to give the AI context
        inventory_df = db.get_all_items()
        from datetime import datetime
        today = datetime.now()

        if inventory_df is not None and not inventory_df.empty:
            # Build a clean inventory summary for the AI
            inventory_summary = f"Total products: {len(inventory_df)}\n"
            inventory_summary += f"Total revenue: ₹{inventory_df['total_revenue'].sum():,.2f}\n\n"
            inventory_summary += "PRODUCT LIST:\n"
            inventory_summary += "ID | Name | Stock | Min Level | Revenue | Expiry\n"
            inventory_summary += "-" * 60 + "\n"
            for _, row in inventory_df.iterrows():
                inventory_summary += f"{row.get('product_id','')} | {row.get('product_name','')} | {row.get('quantity_stock',0)} | {row.get('minimum_stock_level',0)} | ₹{row.get('total_revenue',0)} | {row.get('expiry_date','')}\n"

            # Identify low stock and near-expiry
            low_stock = inventory_df[inventory_df['quantity_stock'].astype(float) <= inventory_df['minimum_stock_level'].astype(float)]
            inventory_summary += f"\nLOW STOCK ITEMS ({len(low_stock)}): {', '.join(low_stock['product_name'].tolist())}\n"
        else:
            inventory_summary = "No inventory data available yet."

        system_prompt = f"""You are a smart AI business assistant for a local Kirana shop (Indian grocery store). 
You can answer questions in Hindi, English, or Hinglish (mixed Hindi-English).
You have access to the shopkeeper's live inventory data shown below.
Be concise, helpful, and friendly. Use ₹ for Indian Rupee. 
If someone asks in Hindi, respond in Hindi. If in English, respond in English.

LIVE INVENTORY DATA (as of today {today.strftime('%d %B %Y')}):
{inventory_summary}

Your role: Help the shopkeeper understand their stock, sales, what to reorder, what is expiring, 
which items are profitable, and give smart business suggestions. Always be practical and specific."""

        client = Groq(api_key=groq_api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=600
        )

        ai_reply = chat_completion.choices[0].message.content

        return jsonify({
            "success": True,
            "reply": ai_reply
        }), 200

    except Exception as e:
        print(f"AI Chat error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"AI Assistant error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
