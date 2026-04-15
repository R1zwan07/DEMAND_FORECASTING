from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
import pandas as pd
import io
import os
import sys
from functools import wraps
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.forecasting import DemandForecaster
from utils.inventory_manager import InventoryManager
from utils.alert_system import AlertSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Initialize components
forecaster = DemandForecaster()
# Use absolute path for inventory file to ensure it's found regardless of working directory
inventory_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_data.csv')
inventory_manager = InventoryManager(inventory_file=inventory_file_path)
alert_system = AlertSystem()

latest_forecast_df = None
forecast_results_all = {}
last_forecast_results = None  # Store complete forecast results for viewing later

# Store the currently selected store (default to None for all stores)
selected_store = None

@app.route('/')
def index():
    """Home page - Dashboard"""
    global selected_store
    
    try:
        # Get store from query parameter if provided
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                selected_store = None
            else:
                selected_store = store_param
        elif selected_store is None and request.args.get('store') is None:
            selected_store = None
        
        # Get alert summary
        alert_summary = alert_system.get_alert_summary(store=selected_store)
        
        # Debug: print the alert_summary to console
        print(f"DEBUG alert_summary: {alert_summary}")
        print(f"DEBUG alert_summary type: {type(alert_summary)}")
        print(f"DEBUG total_unread: {alert_summary.get('total_unread')} type: {type(alert_summary.get('total_unread'))}")
        
        return render_template('index.html', 
                             alert_summary=alert_summary,
                             selected_store=selected_store if selected_store else 'All Stores')
    except Exception as e:
        import traceback
        print(f"Error in index: {e}")
        traceback.print_exc()
        return render_template('index.html', 
                             alert_summary={'total_unread': 0, 'high_priority': 0, 'medium_priority': 0, 'low_priority': 0, 'by_type': {}},
                             selected_store=selected_store if selected_store else 'All Stores')

@app.route('/preview', methods=['POST'])
def preview_data():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Read the CSV file
        df = pd.read_csv(file)
        
        # Print debug info
        print("=" * 60)
        print("FILE UPLOADED - DEBUG INFO")
        print(f"Columns in file: {list(df.columns)}")
        print(f"Number of rows: {len(df)}")
        print("First 5 rows:")
        print(df.head())
        print("=" * 60)
        
        # Check for required columns (exact match as per your CSV)
        required_columns = ['Date', 'Store', 'Product', 'Sales']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'success': False, 
                'error': f'Missing columns: {missing_columns}. Your file has: {list(df.columns)}'
            })
        
        # Get unique values
        products = sorted(df['Product'].dropna().unique().tolist())
        stores = sorted(df['Store'].dropna().unique().tolist())
        
        print(f"Products found: {products}")
        print(f"Stores found: {stores}")
        
        return jsonify({
            'success': True,
            'products': products,
            'stores': stores
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    global latest_forecast_df, forecast_results_all, selected_store
    
    # Handle GET request (store switch from results page)
    if request.method == 'GET':
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                selected_store = None
            else:
                selected_store = store_param
            flash(f'Store changed to: {store_param}', 'info')
        return redirect(url_for('index'))
    
    # Handle POST request (form submission)
    try:
        if 'file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('index'))
        
        product = request.form.get('product')
        store = request.form.get('store')
        
        if not product or not store:
            flash('Please select product and store', 'warning')
            return redirect(url_for('index'))
        
        results, error = forecaster.run_forecast(file, product, store)
        
        if error:
            flash(f'Forecast Error: {error}', 'danger')
            return redirect(url_for('index'))
        
        if not results:
            flash('No results returned from forecast', 'danger')
            return redirect(url_for('index'))
        
        latest_forecast_df = pd.DataFrame(results['forecast'])
        
        forecast_results_all[product] = {
            'total_forecast': results['total_forecast'],
            'avg_forecast': results['avg_forecast'],
            'peak_forecast': results['peak_forecast'],
            'peak_date': results['peak_date']
        }
        
        # Store complete results for later viewing
        global last_forecast_results
        last_forecast_results = results
        
        # Generate inventory data after forecast if it doesn't exist
        if not os.path.exists(inventory_file_path):
            import random
            
            inventory_data = []
            stores_list = ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E']
            products_list = ['Milk', 'Bread', 'Eggs', 'Rice', 'Butter', 'Cheese', 'Juice', 'Yogurt']
            
            for store_item in stores_list:
                for prod in products_list:
                    for batch in range(1, 4):
                        purchase_date = datetime.now() - timedelta(days=random.randint(1, 30))
                        if prod in ['Milk', 'Yogurt', 'Butter']:
                            expiry_days = 7
                        elif prod in ['Bread', 'Juice']:
                            expiry_days = 14
                        elif prod == 'Eggs':
                            expiry_days = 21
                        else:
                            expiry_days = 365
                        
                        expiry_date = purchase_date + timedelta(days=expiry_days)
                        quantity = random.randint(20, 150)
                        
                        inventory_data.append({
                            'store': store_item,
                            'product': prod,
                            'batch_id': f"{prod}_{store_item}_{batch}_{purchase_date.strftime('%Y%m%d')}",
                            'purchase_date': purchase_date,
                            'expiry_date': expiry_date,
                            'quantity': quantity,
                            'unit': 'units',
                            'reorder_level': 20,
                            'reorder_quantity': 50,
                            'daily_consumption_rate': random.randint(10, 30)
                        })
            
            inventory_df = pd.DataFrame(inventory_data)
            inventory_df.to_csv(inventory_file_path, index=False)
            global inventory_manager
            inventory_manager = InventoryManager(inventory_file=inventory_file_path)
        
        # Generate alerts
        alert_system.check_stock_alerts(inventory_manager, forecast_results_all, store=store)
        alert_system.check_forecast_alerts(forecast_results_all, inventory_manager, store=store)
        alert_system.check_expiry_alerts(inventory_manager, store=store)
        alert_system.check_daily_restock_alerts(inventory_manager, store=store)
        
        flash('Forecast completed successfully!', 'success')
        return render_template('results.html', **results, selected_store=store)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/inventory')
def inventory():
    """Inventory management page"""
    global selected_store
    
    try:
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                current_store = None
            else:
                current_store = store_param
                selected_store = current_store
        else:
            current_store = selected_store
        
        if not os.path.exists(inventory_file_path):
            flash('Please upload sales data and run forecast first to generate inventory', 'info')
            return render_template('inventory.html', 
                                 inventory_data=[], 
                                 expiring_soon=[], 
                                 expired_items=[], 
                                 daily_restock=[], 
                                 selected_store=current_store if current_store else 'All Stores')
        
        # Reload inventory data in case it was updated
        inventory_manager.inventory = inventory_manager.load_inventory()
        
        inventory_data = inventory_manager.get_inventory_summary(store=current_store)
        expiring_soon = inventory_manager.get_expiring_soon(days=7, store=current_store)
        expired_items = inventory_manager.get_expired_items(store=current_store)
        daily_restock = inventory_manager.get_daily_restock_items(store=current_store)
        
        return render_template('inventory.html',
                             inventory_data=inventory_data,
                             expiring_soon=expiring_soon.to_dict('records') if len(expiring_soon) > 0 else [],
                             expired_items=expired_items.to_dict('records') if len(expired_items) > 0 else [],
                             daily_restock=daily_restock.to_dict('records') if len(daily_restock) > 0 else [],
                             selected_store=current_store if current_store else 'All Stores')
    except Exception as e:
        print(f"Error in inventory: {e}")
        flash(f'Error loading inventory: {str(e)}', 'danger')
        return render_template('inventory.html', inventory_data=[], expiring_soon=[], expired_items=[], daily_restock=[], selected_store=selected_store if selected_store else 'All Stores')

@app.route('/alerts')
def alerts():
    """Alerts center page"""
    global selected_store
    
    try:
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                current_store = None
            else:
                current_store = store_param
                selected_store = current_store
        else:
            current_store = selected_store
        
        all_alerts = alert_system.get_unread_alerts(store=current_store)
        alert_summary = alert_system.get_alert_summary(store=current_store)
        
        return render_template('alerts.html',
                             alerts=all_alerts,
                             alert_summary=alert_summary,
                             selected_store=current_store if current_store else 'All Stores')
    except Exception as e:
        print(f"Error in alerts: {e}")
        return render_template('alerts.html', alerts=[], alert_summary={'total_unread': 0}, selected_store=selected_store if selected_store else 'All Stores')

@app.route('/mark_alert_read/<int:alert_id>')
def mark_alert_read(alert_id):
    alert_system.mark_as_read(alert_id)
    return redirect(url_for('alerts'))

@app.route('/restock')
def restock():
    """Restock recommendations page"""
    global selected_store
    
    try:
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                current_store = None
            else:
                current_store = store_param
                selected_store = current_store
        else:
            current_store = selected_store
        
        if not os.path.exists(inventory_file_path):
            flash('Please upload sales data and run forecast first to generate inventory', 'info')
            return render_template('restock.html', low_stock_items=[], daily_restock=[], selected_store=current_store if current_store else 'All Stores')
        
        # Reload inventory data in case it was updated
        inventory_manager.inventory = inventory_manager.load_inventory()
        
        low_stock_items = inventory_manager.get_low_stock_items(forecast_results_all, store=current_store)
        daily_restock = inventory_manager.get_daily_restock_items(store=current_store)
        
        return render_template('restock.html',
                             low_stock_items=low_stock_items,
                             daily_restock=daily_restock.to_dict('records') if len(daily_restock) > 0 else [],
                             selected_store=current_store if current_store else 'All Stores')
    except Exception as e:
        print(f"Error in restock: {e}")
        return render_template('restock.html', low_stock_items=[], daily_restock=[], selected_store=selected_store if selected_store else 'All Stores')

@app.route('/expiry')
def expiry():
    """Expiry tracking page"""
    global selected_store
    
    try:
        store_param = request.args.get('store')
        if store_param and store_param in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E', 'All']:
            if store_param == 'All':
                current_store = None
            else:
                current_store = store_param
                selected_store = current_store
        else:
            current_store = selected_store
        
        if not os.path.exists(inventory_file_path):
            flash('Please upload sales data and run forecast first to generate inventory', 'info')
            return render_template('expiry.html', expiring_soon=[], expired_items=[], selected_store=current_store if current_store else 'All Stores')
        
        # Reload inventory data in case it was updated
        inventory_manager.inventory = inventory_manager.load_inventory()
        
        expiring_soon = inventory_manager.get_expiring_soon(days=30, store=current_store)
        expired_items = inventory_manager.get_expired_items(store=current_store)
        
        return render_template('expiry.html',
                             expiring_soon=expiring_soon.to_dict('records') if len(expiring_soon) > 0 else [],
                             expired_items=expired_items.to_dict('records') if len(expired_items) > 0 else [],
                             selected_store=current_store if current_store else 'All Stores')
    except Exception as e:
        print(f"Error in expiry: {e}")
        return render_template('expiry.html', expiring_soon=[], expired_items=[], selected_store=selected_store if selected_store else 'All Stores')

@app.route('/change-store')
def change_store():
    global selected_store
    store = request.args.get('store', 'All')
    if store == 'All':
        selected_store = None
    elif store in ['Store_A', 'Store_B', 'Store_C', 'Store_D', 'Store_E']:
        selected_store = store
    
    flash(f'Store changed to: {store}', 'info')
    return redirect(request.referrer or url_for('index'))

@app.route('/download')
def download_forecast():
    global latest_forecast_df
    
    if latest_forecast_df is None:
        return "No forecast data available", 404
    
    output = io.BytesIO()
    latest_forecast_df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'forecast_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/restock_action', methods=['POST'])
def restock_action():
    global selected_store
    
    try:
        product = request.form.get('product')
        quantity = int(request.form.get('quantity', 0))
        
        if product and quantity > 0:
            inventory_manager.restock_item(product, quantity, store=selected_store)
            flash(f'Successfully restocked {quantity} units of {product}', 'success')
        else:
            flash('Invalid restock request', 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('restock'))

@app.route('/dispose_expired', methods=['POST'])
def dispose_expired():
    global selected_store
    
    try:
        batch_id = request.form.get('batch_id')
        product = request.form.get('product')
        
        if batch_id and product:
            inventory_manager.update_stock(product, batch_id, quantity_sold=999999, store=selected_store)
            flash(f'Disposed expired {product} from batch {batch_id}', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('expiry'))

@app.route('/last_forecast')
def last_forecast():
    """View the last forecast results"""
    global last_forecast_results, selected_store
    
    if last_forecast_results is None:
        flash('No forecast data available. Please run a forecast first.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                         **last_forecast_results, 
                         selected_store=selected_store if selected_store else 'All Stores')

if __name__ == '__main__':
    print("=" * 60)
    print("🏪 Store-Based Demand Forecasting System")
    print("📊 Open http://localhost:5000 in your browser")
    print("=" * 60)
    print("\n📋 CSV Format Required:")
    print("   Columns: Date, Store, Product, Sales")
    print("   Example: 2026-03-01,Store_A,Milk,150")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)