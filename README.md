# Demand Forecasting & Inventory Management System

An AI-powered demand forecasting and inventory management system built with Flask. This application helps retail businesses predict product demand, manage inventory across multiple stores, track expiry dates, and receive automated restock recommendations.

## Features

- **AI-Based Demand Forecasting**: Predict future sales using machine learning
- **Multi-Store Support**: Manage inventory across 5 stores (Store A, B, C, D, E)
- **Inventory Management**: Track stock levels, expiry dates, and batch information
- **Smart Alerts**: Get notified about low stock, expiring products, and restock needs
- **Expiry Tracking**: Monitor product expiry dates and reduce waste
- **Restock Recommendations**: AI-powered suggestions for optimal inventory levels
- **Weekly Sales Summary**: View past sales data with expandable daily breakdown

## Tech Stack

- **Backend**: Flask (Python)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Frontend**: HTML, CSS, JavaScript

## Project Structure

```
demand-forecasting/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── retail_sales_data.csv     # Sample sales data
├── inventory_data.csv        # Generated inventory data
├── README.md                 # This file
├── templates/                # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── results.html
│   ├── inventory.html
│   ├── alerts.html
│   ├── restock.html
│   └── expiry.html
└── utils/                    # Utility modules
    ├── forecasting.py        # Demand forecasting logic
    ├── inventory_manager.py  # Inventory management
    └── alert_system.py       # Alert and notification system
```

## Installation

1. **Clone or download the project** to your local machine

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Upload sales data**:
   - Go to the Dashboard
   - Upload your CSV file (format: Date, Store, Product, Sales)
   - Or use the provided `retail_sales_data.csv`

4. **Run forecast**:
   - Select a product and store
   - Click "Run AI Forecast"
   - View forecast results and inventory insights

5. **Navigate through features**:
   - **Dashboard**: Upload data and view overview
   - **Forecast Results**: View last forecast results
   - **Inventory**: Track stock levels by store
   - **Alerts**: View unread notifications
   - **Restock**: Get restock recommendations
   - **Expiry**: Monitor expiring products

## CSV Format

Your sales data CSV should have the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| Date | Transaction date | 2026-03-01 |
| Store | Store identifier | Store_A |
| Product | Product name | Milk |
| Sales | Units sold | 150 |

Example:
```csv
Date,Store,Product,Sales
2026-03-01,Store_A,Milk,150
2026-03-01,Store_A,Bread,80
2026-03-02,Store_B,Milk,200
```

## Store Filtering

Use the store dropdown in the navigation bar to filter data by:
- All Stores (combined view)
- Store A
- Store B
- Store C
- Store D
- Store E

## Key Functionalities

### 1. Demand Forecasting
- Upload historical sales data
- Get 7-day demand predictions
- View peak demand dates
- See total and average forecast values

### 2. Inventory Management
- View current stock levels by product
- Track batch information
- Monitor days until expiry
- Critical/Low/Good stock status indicators

### 3. Alerts System
- Low stock warnings
- Expiry notifications (7 days, 30 days)
- Daily restock reminders
- Forecast-based shortage predictions

### 4. Expiry Tracking
- Products expiring in 7 days (immediate action)
- Products expiring in 30 days (plan promotions)
- Already expired products (dispose)
- Waste prevention strategies

### 5. Restock Recommendations
- Items below reorder level
- Daily restock requirements for perishables
- Bulk restock suggestions by category
- Estimated costs and lead times

### 6. Past Sales History
- Weekly sales summary by product
- Expandable daily breakdown
- Click on product name to view details
- Last 7 days of sales data

## Development

To modify or extend the application:

1. **Forecasting logic**: Edit `utils/forecasting.py`
2. **Inventory management**: Edit `utils/inventory_manager.py`
3. **Alert system**: Edit `utils/alert_system.py`
4. **UI/UX**: Edit files in `templates/` folder
5. **Styling**: Modify CSS in `templates/base.html`

## License

This project is open source and available for personal and commercial use.

---

**Powered by Machine Learning | Smart Alerts | Expiry Tracking | Auto Restock**
