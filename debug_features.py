import pickle
import pandas as pd
import numpy as np

# Load the model and data
with open('data/tuned_models.pkl', 'rb') as f:
    models = pickle.load(f)

# Check what features the model expects
xgb_model = models['xgb']
feature_cols = models['feature_cols']

print(f"✅ Model expects {len(feature_cols)} features:")
print(f"   {feature_cols[:10]}...")

# Now check what features your uploaded file has
# You'll need to run this with an actual uploaded file
# But first, let's see what's in processed_data
with open('data/processed_data.pkl', 'rb') as f:
    data = pickle.load(f)

print(f"\n📊 Processed data type: {type(data)}")
if isinstance(data, dict):
    print(f"   Keys: {list(data.keys())[:5]}")
    if 'feature_cols' in data:
        print(f"   Data feature_cols: {data['feature_cols'][:5]}")
    if 'X_train' in data:
        print(f"   X_train shape: {data['X_train'].shape}")
