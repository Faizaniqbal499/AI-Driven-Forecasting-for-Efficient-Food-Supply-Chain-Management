# debug_processed.py
import pickle

with open('data/processed_data.pkl', 'rb') as f:
    data = pickle.load(f)

print("Keys in processed_data.pkl:")
if isinstance(data, dict):
    for key in data.keys():
        print(f"  - {key}")
        
    # Check for target scaler
    if 'y_scaler' in data:
        print("\n✅ Found y_scaler!")
    if 'target_scaler' in data:
        print("✅ Found target_scaler!")
    if 'scaler_y' in data:
        print("✅ Found scaler_y!")
        
    # Check the shape of y_train to understand scaling
    if 'y_train_xgb' in data:
        print(f"\ny_train_xgb shape: {data['y_train_xgb'].shape}")
        print(f"y_train_xgb sample: {data['y_train_xgb'][:5]}")
