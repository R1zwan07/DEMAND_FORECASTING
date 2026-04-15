"""
Inventory Management System with Expiry Tracking
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

class InventoryManager:
    def __init__(self, inventory_file='inventory_data.csv'):
        self.inventory_file = inventory_file
        self.inventory = self.load_inventory()
        
    def load_inventory(self):
        """Load inventory data from CSV"""
        if os.path.exists(self.inventory_file):
            df = pd.read_csv(self.inventory_file)
            df['expiry_date'] = pd.to_datetime(df['expiry_date'])
            df['purchase_date'] = pd.to_datetime(df['purchase_date'])
            return df
        else:
            return pd.DataFrame()
    
    def filter_by_store(self, store):
        """Filter inventory by store"""
        if store and 'store' in self.inventory.columns and len(self.inventory) > 0:
            return self.inventory[self.inventory['store'] == store]
        return self.inventory
    
    def get_expiring_soon(self, days=7, store=None):
        """Get products expiring in next N days for a specific store"""
        inventory = self.filter_by_store(store)
        
        if len(inventory) == 0:
            return pd.DataFrame()
            
        today = datetime.now()
        expiry_threshold = today + timedelta(days=days)
        
        if not pd.api.types.is_datetime64_any_dtype(inventory['expiry_date']):
            inventory['expiry_date'] = pd.to_datetime(inventory['expiry_date'])
        
        mask = (inventory['expiry_date'] <= expiry_threshold) & \
               (inventory['expiry_date'] >= today) & \
               (inventory['quantity'] > 0)
        
        expiring = inventory[mask].copy()
        
        if len(expiring) > 0:
            expiring['days_until_expiry'] = (expiring['expiry_date'] - today).dt.days
            expiring['priority'] = expiring['days_until_expiry'].apply(
                lambda x: 'High' if x <= 2 else ('Medium' if x <= 5 else 'Low')
            )
        
        return expiring
    
    def get_expired_items(self, store=None):
        """Get expired items that need disposal for a specific store"""
        inventory = self.filter_by_store(store)
        
        if len(inventory) == 0:
            return pd.DataFrame()
            
        today = datetime.now()
        
        if not pd.api.types.is_datetime64_any_dtype(inventory['expiry_date']):
            inventory['expiry_date'] = pd.to_datetime(inventory['expiry_date'])
        
        mask = (inventory['expiry_date'] < today) & (inventory['quantity'] > 0)
        expired = inventory[mask].copy()
        
        if len(expired) > 0:
            expired['days_expired'] = (today - expired['expiry_date']).dt.days
        
        return expired
    
    def get_low_stock_items(self, forecast_results=None, store=None):
        """Get items with stock below reorder level for a specific store"""
        inventory = self.filter_by_store(store)
        low_stock = []
        
        if len(inventory) == 0:
            return low_stock
        
        inventory['quantity'] = pd.to_numeric(inventory['quantity'], errors='coerce')
        inventory['reorder_level'] = pd.to_numeric(inventory['reorder_level'], errors='coerce')
        inventory['reorder_quantity'] = pd.to_numeric(inventory['reorder_quantity'], errors='coerce')
        inventory['daily_consumption_rate'] = pd.to_numeric(inventory['daily_consumption_rate'], errors='coerce')
        
        for idx, row in inventory.iterrows():
            if row['quantity'] <= row['reorder_level']:
                forecast_qty = 0
                if forecast_results and row['product'] in forecast_results:
                    forecast_qty = forecast_results[row['product']]['total_forecast']
                
                low_stock.append({
                    'product': row['product'],
                    'batch_id': row['batch_id'],
                    'current_stock': row['quantity'],
                    'reorder_level': row['reorder_level'],
                    'reorder_quantity': row['reorder_quantity'],
                    'forecast_demand': forecast_qty,
                    'expiry_date': row['expiry_date'].strftime('%Y-%m-%d') if hasattr(row['expiry_date'], 'strftime') else str(row['expiry_date']),
                    'days_until_expiry': (row['expiry_date'] - datetime.now()).days if hasattr(row['expiry_date'], 'strftime') else 0,
                    'daily_consumption_rate': row['daily_consumption_rate']
                })
        
        return low_stock
    
    def get_daily_restock_items(self, store=None):
        """Get items that need daily restocking for a specific store"""
        inventory = self.filter_by_store(store)
        
        if len(inventory) == 0:
            return pd.DataFrame()
            
        perishable_products = ['Milk', 'Yogurt', 'Bread', 'Juice', 'Butter']
        
        inventory['quantity'] = pd.to_numeric(inventory['quantity'], errors='coerce')
        inventory['daily_consumption_rate'] = pd.to_numeric(inventory['daily_consumption_rate'], errors='coerce')
        
        mask = inventory['product'].isin(perishable_products)
        daily_items = inventory[mask].copy()
        
        if len(daily_items) > 0:
            daily_items['restock_needed'] = daily_items['quantity'] < (daily_items['daily_consumption_rate'] * 2)
            daily_items['suggested_restock'] = daily_items['daily_consumption_rate'] * 3
            daily_items = daily_items[daily_items['restock_needed'] == True]
        
        return daily_items
    
    def update_stock(self, product, batch_id, quantity_sold, store=None):
        """Update inventory after sales"""
        inventory = self.filter_by_store(store)
        mask = (inventory['product'] == product) & (inventory['batch_id'] == batch_id)
        
        if mask.any():
            current_qty = inventory.loc[mask, 'quantity'].iloc[0]
            new_qty = max(0, current_qty - quantity_sold)
            inventory.loc[mask, 'quantity'] = new_qty
            inventory.to_csv(self.inventory_file, index=False)
            self.inventory = inventory
            return True
        return False
    
    def restock_item(self, product, quantity, store=None, batch_id=None):
        """Add new stock to inventory"""
        if batch_id is None:
            batch_id = f"{product}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if product in ['Milk', 'Yogurt', 'Butter']:
            expiry_days = 7
        elif product in ['Bread', 'Juice']:
            expiry_days = 14
        elif product in ['Eggs']:
            expiry_days = 21
        else:
            expiry_days = 365
        
        daily_rate = 15
        if len(self.inventory) > 0:
            product_data = self.inventory[self.inventory['product'] == product]
            if len(product_data) > 0:
                daily_rate = product_data['daily_consumption_rate'].iloc[0]
        
        new_entry = {
            'store': store if store else 'Store_A',
            'product': product,
            'batch_id': batch_id,
            'purchase_date': datetime.now(),
            'expiry_date': datetime.now() + timedelta(days=expiry_days),
            'quantity': quantity,
            'unit': 'units',
            'reorder_level': 20,
            'reorder_quantity': 50,
            'daily_consumption_rate': daily_rate
        }
        
        self.inventory = pd.concat([self.inventory, pd.DataFrame([new_entry])], ignore_index=True)
        self.inventory.to_csv(self.inventory_file, index=False)
        
        return new_entry
    
    def get_inventory_summary(self, store=None):
        """Get summary of current inventory for a specific store"""
        inventory = self.filter_by_store(store)
        
        if len(inventory) == 0:
            return []
        
        inventory['quantity'] = pd.to_numeric(inventory['quantity'], errors='coerce')
        inventory['expiry_date'] = pd.to_datetime(inventory['expiry_date'], errors='coerce')
        
        summary = inventory.groupby('product').agg({
            'quantity': 'sum',
            'expiry_date': lambda x: (min(x) - datetime.now()).days if len(x) > 0 and pd.notna(min(x)) else 365,
            'batch_id': 'count'
        }).rename(columns={
            'quantity': 'total_stock',
            'expiry_date': 'days_until_earliest_expiry',
            'batch_id': 'batch_count'
        }).reset_index()
        
        summary['total_stock'] = pd.to_numeric(summary['total_stock'], errors='coerce').fillna(0)
        summary['days_until_earliest_expiry'] = pd.to_numeric(summary['days_until_earliest_expiry'], errors='coerce').fillna(365)
        
        summary['status'] = summary['total_stock'].apply(
            lambda x: 'Critical' if x < 20 else ('Low' if x < 50 else 'Good')
        )
        
        return summary.to_dict('records')