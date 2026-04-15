"""
Alert and Notification System
"""

from datetime import datetime, timedelta
import json
import os
import pandas as pd

class AlertSystem:
    def __init__(self, alert_file='alerts.json'):
        self.alert_file = alert_file
        self.alerts = self.load_alerts()
        
    def load_alerts(self):
        """Load existing alerts"""
        if os.path.exists(self.alert_file):
            try:
                with open(self.alert_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_alerts(self):
        """Save alerts to file"""
        with open(self.alert_file, 'w') as f:
            json.dump(self.alerts, f, indent=2, default=str)
    
    def add_alert(self, alert_type, title, message, priority, product=None, store=None):
        """Add a new alert"""
        alert = {
            'id': len(self.alerts) + 1,
            'type': alert_type,
            'title': title,
            'message': message,
            'priority': priority,
            'product': product,
            'store': store,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        self.alerts.append(alert)
        self.save_alerts()
        
        # Print to console for demo
        self.print_alert(alert)
        
        return alert
    
    def print_alert(self, alert):
        """Print alert to console"""
        print("\n" + "="*60)
        print(f"🔔 {alert['type'].upper()} ALERT - Priority: {alert['priority']}")
        if alert.get('store'):
            print(f"🏬 Store: {alert['store']}")
        print(f"📢 {alert['title']}")
        print(f"📝 {alert['message']}")
        print(f"⏰ {alert['timestamp']}")
        print("="*60 + "\n")
    
    def check_stock_alerts(self, inventory_manager, forecast_results=None, store=None):
        """Check for low stock and generate alerts"""
        low_stock_items = inventory_manager.get_low_stock_items(forecast_results, store=store)
        
        for item in low_stock_items:
            # Check if alert already exists for this product
            existing = [a for a in self.alerts 
                       if a.get('product') == item['product'] 
                       and a['type'] == 'stock' 
                       and not a['read']
                       and (a.get('store') == store or store is None)]
            
            if not existing:
                priority = 'High' if item['current_stock'] < item['reorder_level'] / 2 else 'Medium'
                
                # Calculate days until stockout
                daily_rate = item.get('daily_consumption_rate', 10)
                days_until_empty = int(item['current_stock'] / daily_rate) if daily_rate > 0 else 0
                
                self.add_alert(
                    alert_type='stock',
                    title=f"⚠️ Low Stock Alert: {item['product']}",
                    message=f"Current stock: {item['current_stock']} units. "
                           f"Reorder level: {item['reorder_level']}. "
                           f"Will run out in approximately {days_until_empty} days. "
                           f"Recommended restock: {item['reorder_quantity']} units.",
                    priority=priority,
                    product=item['product'],
                    store=store
                )
    
    def check_expiry_alerts(self, inventory_manager, store=None):
        """Check for expiring products and generate alerts"""
        expiring_soon = inventory_manager.get_expiring_soon(days=7, store=store)
        
        if len(expiring_soon) > 0:
            for _, item in expiring_soon.iterrows():
                existing = [a for a in self.alerts 
                           if a.get('product') == item['product'] 
                           and a['type'] == 'expiry' 
                           and not a['read']
                           and (a.get('store') == store or store is None)]
                
                if not existing:
                    priority = item['priority']
                    
                    self.add_alert(
                        alert_type='expiry',
                        title=f"⚠️ Product Expiring Soon: {item['product']}",
                        message=f"Batch {item['batch_id']} expires in {item['days_until_expiry']} days. "
                               f"Quantity: {item['quantity']} units. "
                               f"Expiry date: {item['expiry_date'].strftime('%Y-%m-%d')}. "
                               f"Consider running a promotion or discount to clear stock.",
                        priority=priority,
                        product=item['product'],
                        store=store
                    )
        
        # Check for already expired items
        expired_items = inventory_manager.get_expired_items(store=store)
        if len(expired_items) > 0:
            for _, item in expired_items.iterrows():
                self.add_alert(
                    alert_type='expiry',
                    title=f"❌ EXPIRED PRODUCT: {item['product']}",
                    message=f"Batch {item['batch_id']} expired {item['days_expired']} days ago. "
                           f"Quantity to dispose: {item['quantity']} units. "
                           f"Please remove from shelf immediately.",
                    priority='High',
                    product=item['product'],
                    store=store
                )
    
    def check_daily_restock_alerts(self, inventory_manager, store=None):
        """Generate daily restock alerts for perishable items"""
        daily_items = inventory_manager.get_daily_restock_items(store=store)
        
        if len(daily_items) > 0:
            for _, item in daily_items.iterrows():
                existing = [a for a in self.alerts 
                           if a.get('product') == item['product'] 
                           and a['type'] == 'restock' 
                           and not a['read']
                           and (a.get('store') == store or store is None)]
                
                if not existing:
                    self.add_alert(
                        alert_type='restock',
                        title=f"🥛 Daily Restock Needed: {item['product']}",
                        message=f"This item needs daily restocking. Current stock: {item['quantity']} units. "
                               f"Daily consumption: {item['daily_consumption_rate']} units. "
                               f"Suggested restock: {item['suggested_restock']} units for next 3 days.",
                        priority='High',
                        product=item['product'],
                        store=store
                    )
    
    def check_forecast_alerts(self, forecast_results, inventory_manager, store=None):
        """Generate alerts based on forecast predictions"""
        for product, forecast in forecast_results.items():
            if forecast['total_forecast'] > 0:
                inventory = inventory_manager.filter_by_store(store)
                product_data = inventory[inventory['product'] == product] if len(inventory) > 0 else pd.DataFrame()
                current_stock = product_data['quantity'].sum() if len(product_data) > 0 else 0
                
                if current_stock < forecast['total_forecast']:
                    shortage = forecast['total_forecast'] - current_stock
                    
                    existing = [a for a in self.alerts 
                               if a.get('product') == product 
                               and a['type'] == 'forecast' 
                               and not a['read']
                               and (a.get('store') == store or store is None)]
                    
                    if not existing:
                        self.add_alert(
                            alert_type='forecast',
                            title=f"📊 Stock Shortage Predicted: {product}",
                            message=f"Based on AI forecast, you'll need {forecast['total_forecast']:.0f} units in next 7 days. "
                                   f"Current stock: {current_stock:.0f} units. "
                                   f"Shortage: {shortage:.0f} units. "
                                   f"Recommended: Order {shortage + forecast['avg_forecast'] * 2:.0f} units.",
                            priority='High',
                            product=product,
                            store=store
                        )
    
    def get_unread_alerts(self, store=None):
        """Get all unread alerts, optionally filtered by store"""
        alerts = [a for a in self.alerts if not a['read']]
        if store:
            alerts = [a for a in alerts if a.get('store') == store or a.get('store') is None]
        return alerts
    
    def mark_as_read(self, alert_id):
        """Mark alert as read"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['read'] = True
        self.save_alerts()
    
    def get_alerts_by_type(self, alert_type, store=None):
        """Get alerts filtered by type"""
        alerts = [a for a in self.alerts if a['type'] == alert_type]
        if store:
            alerts = [a for a in alerts if a.get('store') == store or a.get('store') is None]
        return alerts
    
    def get_alert_summary(self, store=None):
        """Get summary of alerts"""
        unread = self.get_unread_alerts(store=store)
        
        summary = {
            'total_unread': int(len(unread)),
            'high_priority': int(len([a for a in unread if a.get('priority') == 'High'])),
            'medium_priority': int(len([a for a in unread if a.get('priority') == 'Medium'])),
            'low_priority': int(len([a for a in unread if a.get('priority') == 'Low'])),
            'by_type': {
                'stock': int(len([a for a in unread if a.get('type') == 'stock'])),
                'expiry': int(len([a for a in unread if a.get('type') == 'expiry'])),
                'restock': int(len([a for a in unread if a.get('type') == 'restock'])),
                'forecast': int(len([a for a in unread if a.get('type') == 'forecast']))
            }
        }
        
        return summary