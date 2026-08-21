# feature_engineering.py
import pandas as pd
import numpy as np

def prepare_features_for_prediction(df):
    """Transform raw data into model-ready features"""
    data = df.copy()
    
    # Create date column
    if 'date' in data.columns:
        data['date'] = pd.to_datetime(data['date'])
    else:
        data['date'] = pd.Timestamp.now()
    
    # Time features
    data['week_of_year'] = data['date'].dt.isocalendar().week
    data['month'] = data['date'].dt.month
    data['quarter'] = data['date'].dt.quarter
    data['day_of_week'] = data['date'].dt.dayofweek
    data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
    
    # Cyclical features
    data['week_sin'] = np.sin(2 * np.pi * data['week_of_year'] / 52)
    data['week_cos'] = np.cos(2 * np.pi * data['week_of_year'] / 52)
    data['month_sin'] = np.sin(2 * np.pi * data['month'] / 12)
    data['month_cos'] = np.cos(2 * np.pi * data['month'] / 12)
    
    # Price features
    data['price'] = data.get('checkout_price', data.get('base_price', 100))
    data['price_diff'] = data.get('checkout_price', 100) - data.get('base_price', 100)
    data['discount_percent'] = (data['price_diff'] / data.get('base_price', 100)) * 100
    
    # Demand features (default values if not present)
    if 'demand' in data.columns:
        data['demand_lag_1'] = data['demand'].shift(1).fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
        data['demand_lag_2'] = data['demand'].shift(2).fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
        data['demand_lag_3'] = data['demand'].shift(3).fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
        data['demand_lag_7'] = data['demand'].shift(7).fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
        data['demand_ma_3'] = data['demand'].rolling(3).mean().fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
        data['demand_ma_7'] = data['demand'].rolling(7).mean().fillna(data['demand'].mean() if not data['demand'].isna().all() else 150)
    else:
        # Default values when no demand history
        data['demand_lag_1'] = 150
        data['demand_lag_2'] = 150
        data['demand_lag_3'] = 150
        data['demand_lag_7'] = 150
        data['demand_ma_3'] = 150
        data['demand_ma_7'] = 150
    
    # EXACT 19 features the model expects
    feature_cols = [
        'week_of_year', 'month', 'quarter', 'week_sin', 'week_cos',
        'month_sin', 'month_cos', 'day_of_week', 'is_weekend',
        'price', 'price_diff', 'discount_percent',
        'demand_lag_1', 'demand_lag_2', 'demand_lag_3', 'demand_lag_7',
        'demand_ma_3', 'demand_ma_7', 'center_encoded'  # ← This is the 19th feature
    ]
    
    # Add center_encoded if available, otherwise use 0
    if 'center_id' in data.columns:
        data['center_encoded'] = data['center_id'].astype('category').cat.codes
    else:
        data['center_encoded'] = 0
    
    # Verify we have all 19 features
    result = data[feature_cols].copy()
    print(f"✅ Created {len(result.columns)} features: {list(result.columns)}")
    
    return result, feature_cols