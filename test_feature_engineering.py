import pickle
import pandas as pd
from feature_engineering import prepare_features_for_prediction

# Load the model
with open('data/tuned_models.pkl', 'rb') as f:
    models = pickle.load(f)

# Create sample data matching your uploaded file format
sample_data = pd.DataFrame({
    'week': [1, 2, 3],
    'center_id': [1, 1, 2],
    'meal_id': [100, 101, 100],
    'checkout_price': [100, 110, 105],
    'base_price': [120, 120, 115],
    'demand': [150, 160, 155]  # Optional
})

print("Original data columns:", list(sample_data.columns))

# Apply feature engineering
engineered_features, feature_names = prepare_features_for_prediction(sample_data)

print(f"\nEngineered {len(feature_names)} features:")
print("Feature names:", feature_names[:10], "...")
print(f"\nEngineered data shape: {engineered_features.shape}")

# Test prediction
xgb_model = models['xgb']
predictions = xgb_model.predict(engineered_features)
print(f"\n🔮 Predictions: {predictions}")
