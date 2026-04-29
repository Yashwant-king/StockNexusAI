import pandas as pd
import os
from datetime import datetime, timedelta

def load_inventory_data(data_path='data_set/data.csv'):
    """Load inventory data from CSV file"""
    try:
        print(f"Loading inventory data from: {data_path}")
        if not os.path.exists(data_path):
            print(f"Data file not found: {data_path}")
            return None
        
        df = pd.read_csv(data_path)
        print(f"Loaded {len(df)} rows of data")
        print(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"Error loading inventory data: {str(e)}")
        return None

def get_low_stock_products(df, threshold=None):
    """Get products with low stock levels (below their minimum_stock_level)"""
    try:
        if threshold is not None:
            low_stock = df[df['quantity_stock'] <= threshold][
                ['product_id', 'product_name', 'quantity_stock', 'minimum_stock_level']
            ]
        else:
            # Use each product's own minimum_stock_level
            low_stock = df[df['quantity_stock'].astype(float) <= df['minimum_stock_level'].astype(float)][
                ['product_id', 'product_name', 'quantity_stock', 'minimum_stock_level']
            ]
        return low_stock.to_dict(orient='records')
    except Exception as e:
        print(f"Error getting low stock products: {str(e)}")
        return []

def get_near_expiry_products(df, days_threshold=7):
    """Get products nearing expiry"""
    try:
        # Try multiple date formats for robustness
        today = pd.Timestamp.today()
        expiry_dates = pd.to_datetime(df['expiry_date'], format='%d/%m/%y', errors='coerce')
        # Retry with other formats for NaT values
        mask_nat = expiry_dates.isna()
        if mask_nat.any():
            expiry_dates[mask_nat] = pd.to_datetime(df.loc[mask_nat, 'expiry_date'], format='%d/%m/%Y', errors='coerce')
        mask_nat = expiry_dates.isna()
        if mask_nat.any():
            expiry_dates[mask_nat] = pd.to_datetime(df.loc[mask_nat, 'expiry_date'], format='%Y-%m-%d', errors='coerce')
        
        df = df.copy()
        df['expiry_date'] = expiry_dates
        df['days_until_expiry'] = (df['expiry_date'] - today).dt.days
        
        # Filter products expiring within threshold
        near_expiry = df[df['days_until_expiry'] <= days_threshold][
            ['product_id', 'product_name', 'expiry_date', 'days_until_expiry', 'quantity_stock']
        ]
        
        return near_expiry.to_dict(orient='records')
    except Exception as e:
        print(f"Error getting near expiry products: {str(e)}")
        return []

def calculate_inventory_metrics(df):
    """Calculate comprehensive inventory metrics"""
    try:
        print(f"Calculating metrics for {len(df)} products")
        metrics = {}
        
        # Basic counts
        metrics['total_products'] = int(len(df))
        metrics['low_stock_count'] = int(len(df[df['quantity_stock'].astype(float) <= df['minimum_stock_level'].astype(float)]))
        
        # Stock levels
        metrics['average_stock_level'] = float(df['quantity_stock'].mean())
        metrics['total_stock_value'] = float(df['total_revenue'].astype(float).sum())
        
        # Expiry analysis
        try:
            expiry_dates = pd.to_datetime(df['expiry_date'], format='%d/%m/%y', errors='coerce')
            mask_nat = expiry_dates.isna()
            if mask_nat.any():
                expiry_dates[mask_nat] = pd.to_datetime(df.loc[mask_nat, 'expiry_date'], format='%d/%m/%Y', errors='coerce')
            mask_nat = expiry_dates.isna()
            if mask_nat.any():
                expiry_dates[mask_nat] = pd.to_datetime(df.loc[mask_nat, 'expiry_date'], format='%Y-%m-%d', errors='coerce')
            today = pd.Timestamp.today()
            days_until = (expiry_dates - today).dt.days
            metrics['near_expiry_count'] = int((days_until <= 7).sum())
        except:
            metrics['near_expiry_count'] = 0
        
        # Sales metrics
        metrics['total_revenue'] = float(df['total_revenue'].astype(float).sum())
        metrics['average_order_value'] = float(df['total_revenue'].astype(float).mean())
        
        print(f"Calculated metrics: {metrics}")
        return metrics
    except Exception as e:
        print(f"Error calculating inventory metrics: {str(e)}")
        return {
            'total_products': 0,
            'low_stock_count': 0,
            'average_stock_level': 0.0,
            'total_stock_value': 0.0,
            'near_expiry_count': 0,
            'total_revenue': 0.0,
            'average_order_value': 0.0
        }

def generate_inventory_report(data_path='data_set/data.csv'):
    """Generate comprehensive inventory report"""
    try:
        df = load_inventory_data(data_path)
        if df is None:
            return None
        
        metrics = calculate_inventory_metrics(df)
        low_stock = get_low_stock_products(df)
        near_expiry = get_near_expiry_products(df)
        
        report = {
            'metrics': metrics,
            'low_stock_products': low_stock,
            'near_expiry_products': near_expiry,
            'generated_at': datetime.now().isoformat(),
            'total_products_analyzed': len(df)
        }
        
        return report
    except Exception as e:
        print(f"Error generating inventory report: {str(e)}")
        return None

def validate_csv_data(df):
    """Validate CSV data structure and content"""
    try:
        required_columns = [
            'product_id', 'product_name', 'quantity_stock', 
            'minimum_stock_level', 'total_revenue'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        # Check for empty values in critical columns
        if df['product_id'].isnull().any():
            return False, "Product ID cannot be null"
        
        if df['product_name'].isnull().any():
            return False, "Product name cannot be null"
        
        # Check for negative stock levels
        if (df['quantity_stock'] < 0).any():
            return False, "Stock levels cannot be negative"
        
        return True, "Data validation passed"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def get_stock_alerts(df):
    """Get stock alerts and recommendations"""
    try:
        alerts = []
        
        # Low stock alerts
        low_stock = df[df['quantity_stock'] <= 50]
        for _, product in low_stock.iterrows():
            alerts.append({
                'type': 'critical',
                'message': f"Critical: {product['product_name']} has only {product['quantity_stock']} units in stock",
                'product_id': product['product_id'],
                'severity': 'high'
            })
        
        # Near expiry alerts
        try:
            df['expiry_date'] = pd.to_datetime(df['expiry_date'], format='%d/%m/%y', errors='coerce')
            today = pd.Timestamp.today()
            df['days_until_expiry'] = (df['expiry_date'] - today).dt.days
            
            near_expiry = df[df['days_until_expiry'] <= 3]
            for _, product in near_expiry.iterrows():
                alerts.append({
                    'type': 'expiry',
                    'message': f"Expiring soon: {product['product_name']} expires in {product['days_until_expiry']} days",
                    'product_id': product['product_id'],
                    'severity': 'medium'
                })
        except:
            pass
        
        return alerts
    except Exception as e:
        print(f"Error getting stock alerts: {str(e)}")
        return []

def format_currency(amount):
    """Format amount as Indian Rupee currency"""
    try:
        return f"\u20b9{amount:,.2f}"
    except:
        return str(amount)

def format_number(number):
    """Format number with commas"""
    try:
        return f"{number:,.0f}"
    except:
        return str(number) 