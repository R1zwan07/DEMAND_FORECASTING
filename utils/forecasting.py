"""
Demand Forecasting ML Utilities - Enhanced for Multiple Products
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DemandForecaster:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.df_processed = None
        
    def load_data(self, file):
        """Load and validate CSV file"""
        try:
            df = pd.read_csv(file)
            
            # Standardize column names - convert to lowercase and strip spaces
            df.columns = df.columns.str.lower().str.strip()
            
            # Print available columns for debugging
            print(f"Available columns in uploaded file: {list(df.columns)}")
            
            # Map expected columns with various possible names
            col_mapping = {
                'date': ['date', 'transaction_date', 'order_date', 'day', 'datetime'],
                'store': ['store', 'store_name', 'location', 'branch', 'outlet'],
                'product': ['product', 'item', 'sku', 'product_name', 'product_id', 'name'],
                'sales': ['sales', 'demand', 'quantity', 'units', 'qty', 'sold', 'volume']
            }
            
            # Find matching columns
            for target, possible_names in col_mapping.items():
                for col in df.columns:
                    if col in possible_names:
                        if target not in df.columns:
                            df.rename(columns={col: target}, inplace=True)
                        break
            
            # Debug: Show renamed columns
            print(f"Columns after mapping: {list(df.columns)}")
            
            # Validate required columns
            missing_cols = []
            required_cols = ['date', 'sales']
            for col in required_cols:
                if col not in df.columns:
                    missing_cols.append(col)
            
            if missing_cols:
                return None, f"Missing required columns: {missing_cols}. Found columns: {list(df.columns)}. Please ensure your CSV has Date and Sales columns."
            
            # Add default columns if missing
            if 'product' not in df.columns:
                # Try to detect product column
                if 'item' in df.columns:
                    df.rename(columns={'item': 'product'}, inplace=True)
                else:
                    df['product'] = 'Product_1'
                    print("No product column found, using default 'Product_1'")
            
            if 'store' not in df.columns:
                # Try to detect store column
                if 'location' in df.columns:
                    df.rename(columns={'location': 'store'}, inplace=True)
                else:
                    df['store'] = 'Store_1'
                    print("No store column found, using default 'Store_1'")
            
            # Convert date column
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                # Drop rows with invalid dates
                initial_len = len(df)
                df = df.dropna(subset=['date'])
                if len(df) < initial_len:
                    print(f"Dropped {initial_len - len(df)} rows with invalid dates")
            except Exception as e:
                return None, f"Error converting dates: {str(e)}. Please ensure your date column is in a standard format (YYYY-MM-DD)."
            
            # Convert sales to numeric
            try:
                df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
                df = df.dropna(subset=['sales'])
            except Exception as e:
                return None, f"Error converting sales to numbers: {str(e)}"
            
            if len(df) == 0:
                return None, "No valid data rows after cleaning. Please check your CSV format."
            
            # Sort by date
            df = df.sort_values('date')
            
            print(f"Successfully loaded {len(df)} records")
            print(f"Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"Products found: {df['product'].unique()}")
            print(f"Stores found: {df['store'].unique()}")
                
            return df, None
            
        except Exception as e:
            return None, f"Error loading file: {str(e)}"
    
    def get_product_summary(self, df, store=None):
        """Get summary statistics for each product, optionally filtered by store"""
        # Filter by store if provided
        if store and store != 'All':
            df = df[df['store'] == store].copy()
        
        if df.empty:
            return []
        
        # Calculate summary for each product in this store
        products_list = []
        for product in df['product'].unique():
            product_data = df[df['product'] == product]
            avg_daily = product_data['sales'].mean()
            total_sales = product_data['sales'].sum()
            
            # Calculate trend
            product_data_sorted = product_data.sort_values('date')
            if len(product_data_sorted) >= 14:
                recent_avg = product_data_sorted.tail(7)['sales'].mean()
                older_avg = product_data_sorted.head(7)['sales'].mean()
                if recent_avg > older_avg * 1.1:
                    trend = "📈 Growing"
                elif recent_avg < older_avg * 0.9:
                    trend = "📉 Declining"
                else:
                    trend = "➡️ Stable"
            else:
                trend = "➡️ Stable"
            
            # Get weekly sales summary (last 7 days)
            past_week = product_data.sort_values('date').tail(7)
            weekly_total = past_week['sales'].sum()
            
            # Get daily breakdown for expandable view
            daily_breakdown = []
            for _, row in past_week.iterrows():
                daily_breakdown.append({
                    'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    'sales': int(row['sales'])
                })
            
            products_list.append({
                'product': product,
                'avg_daily_sales': f"{avg_daily:.2f} units",
                'total_sales': f"{total_sales:.0f} units",
                'trend': trend,
                'weekly_sales': int(weekly_total),
                'daily_breakdown': daily_breakdown
            })
        
        return products_list
    
    def preprocess_data(self, df):
        """Clean and preprocess data"""
        df = df.copy()
        df = df.sort_values('date')
        df['sales'] = df['sales'].fillna(df['sales'].median())
        
        # Remove outliers using IQR (only if enough data)
        if len(df) > 10:
            Q1 = df['sales'].quantile(0.25)
            Q3 = df['sales'].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df['sales'] = df['sales'].clip(lower_bound, upper_bound)
        
        return df
    
    def feature_engineering(self, df):
        """Create features for time series prediction"""
        df = df.copy()
        
        # Time-based features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['day_of_month'] = df['date'].dt.day
        df['week_of_year'] = df['date'].dt.isocalendar().week
        
        # Lag features
        df['sales_lag_1'] = df['sales'].shift(1)
        df['sales_lag_7'] = df['sales'].shift(7)
        
        # Rolling statistics
        df['rolling_mean_7'] = df['sales'].rolling(window=7).mean()
        df['rolling_std_7'] = df['sales'].rolling(window=7).std()
        
        # Drop rows with NaN values
        df = df.dropna()
        
        if len(df) < 7:
            raise ValueError(f"Not enough data! Need at least 7 days, only have {len(df)} days.")
        
        self.feature_columns = ['day_of_week', 'month', 'day_of_month', 'week_of_year',
                                'sales_lag_1', 'sales_lag_7', 'rolling_mean_7', 'rolling_std_7']
        
        return df
    
    def train_model(self, X_train, y_train):
        """Train Random Forest model"""
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        return model
    
    def predict_future(self, model, last_data, days=7):
        """Predict next N days"""
        future_predictions = []
        current_data = last_data.copy()
        
        for i in range(days):
            future_date = current_data['date'].max() + timedelta(days=1)
            
            # Prepare features
            features = current_data[self.feature_columns].iloc[-1:].copy()
            
            # Make prediction
            pred = model.predict(features)[0]
            
            # Store prediction
            future_predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_sales': max(0, round(pred, 2))
            })
            
            # Update data for next iteration
            new_row = current_data.iloc[-1:].copy()
            new_row['date'] = future_date
            new_row['sales'] = pred
            new_row['sales_lag_1'] = current_data['sales'].iloc[-1]
            new_row['sales_lag_7'] = current_data['sales'].iloc[-7] if len(current_data) >= 7 else pred
            new_row['rolling_mean_7'] = current_data['sales'].rolling(7).mean().iloc[-1]
            new_row['rolling_std_7'] = current_data['sales'].rolling(7).std().iloc[-1]
            new_row['day_of_week'] = future_date.dayofweek
            new_row['month'] = future_date.month
            new_row['day_of_month'] = future_date.day
            new_row['week_of_year'] = future_date.isocalendar().week
            
            current_data = pd.concat([current_data, new_row], ignore_index=True)
        
        return pd.DataFrame(future_predictions)
    
    def evaluate_model(self, y_true, y_pred):
        """Calculate evaluation metrics"""
        if len(y_true) == 0 or len(y_pred) == 0:
            return {'MAE': 0, 'RMSE': 0, 'MAPE': 0}
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
        
        return {
            'MAE': round(mae, 2),
            'RMSE': round(rmse, 2),
            'MAPE': round(mape, 1)
        }
    
    def analyze_trend(self, historical, forecast):
        """Analyze demand trend"""
        if len(historical) < 7:
            return "➡️ Stable", "warning"
        
        recent_avg = historical.tail(7)['sales'].mean()
        forecast_avg = forecast['predicted_sales'].mean()
        
        if forecast_avg > recent_avg * 1.1:
            return "📈 Increasing", "success"
        elif forecast_avg < recent_avg * 0.9:
            return "📉 Decreasing", "danger"
        else:
            return "➡️ Stable", "warning"
    
    def run_forecast(self, file, product, store):
        """Main forecasting pipeline"""
        try:
            # Load data
            df_raw, error = self.load_data(file)
            if error:
                return None, error
            
            # Get product summary for selected store only
            product_summary = self.get_product_summary(df_raw, store)
            
            # Filter data for specific product/store
            df_filtered = df_raw[
                (df_raw['product'] == product) & 
                (df_raw['store'] == store)
            ].copy()
            
            if df_filtered.empty:
                return None, f"No data found for product '{product}' and store '{store}'. Available products: {list(df_raw['product'].unique())}, Available stores: {list(df_raw['store'].unique())}"
            
            print(f"Found {len(df_filtered)} records for {product} at {store}")
            
            # Preprocess
            df_processed = self.preprocess_data(df_filtered)
            
            # Feature engineering
            df_features = self.feature_engineering(df_processed)
            
            # Train-test split
            train_size = int(len(df_features) * 0.8)
            train_data = df_features[:train_size]
            test_data = df_features[train_size:]
            
            # Prepare features
            X_train = train_data[self.feature_columns]
            y_train = train_data['sales']
            X_test = test_data[self.feature_columns] if len(test_data) > 0 else None
            y_test = test_data['sales'] if len(test_data) > 0 else None
            
            # Train model
            self.model = self.train_model(X_train, y_train)
            
            # Make predictions
            y_pred_test = self.model.predict(X_test) if X_test is not None else None
            
            # Evaluate model
            test_metrics = self.evaluate_model(y_test, y_pred_test) if y_test is not None else None
            
            # Predict future
            future_forecast = self.predict_future(self.model, df_features, days=7)
            
            # Analyze trend
            trend, trend_color = self.analyze_trend(df_processed, future_forecast)
            
            # Prepare results
            results = {
                'product': product,
                'store': store,
                'metrics': test_metrics if test_metrics else {'MAE': 0, 'RMSE': 0, 'MAPE': 0},
                'forecast': future_forecast.to_dict('records'),
                'trend': trend,
                'trend_color': trend_color,
                'historical': df_processed[['date', 'sales']].to_dict('records'),
                'test_data': test_data[['date', 'sales']].to_dict('records') if len(test_data) > 0 else [],
                'predictions': y_pred_test.tolist() if y_pred_test is not None else [],
                'avg_sales': round(df_processed['sales'].mean(), 2),
                'total_records': len(df_processed),
                'product_summary': product_summary,
                'total_forecast': round(future_forecast['predicted_sales'].sum(), 2),
                'avg_forecast': round(future_forecast['predicted_sales'].mean(), 2),
                'peak_forecast': round(future_forecast['predicted_sales'].max(), 2),
                'peak_date': future_forecast.loc[future_forecast['predicted_sales'].idxmax(), 'date']
            }
            
            return results, None
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, str(e)