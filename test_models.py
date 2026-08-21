import pickle
import numpy as np
import tensorflow as tf
import xgboost as xgb

print(f"TensorFlow version: {tf.__version__}")
print(f"XGBoost version: {xgb.__version__}")

# Load the full tuned_models.pkl
try:
    with open('data/tuned_models.pkl', 'rb') as f:
        models = pickle.load(f)
    
    print(f"\n✅ Models loaded successfully!")
    print(f"Keys: {list(models.keys())}")
    
    # Test XGBoost
    if 'xgb' in models:
        xgb_model = models['xgb']
        print(f"\n📊 XGBoost type: {type(xgb_model)}")
        test_input = np.zeros((1, 19))
        pred = xgb_model.predict(test_input)
        print(f"🔮 XGBoost test prediction: {pred[0]}")
    
    # Test LSTM
    if 'lstm' in models:
        lstm_model = models['lstm']
        print(f"\n📊 LSTM type: {type(lstm_model)}")
        # LSTM needs sequence data
        print(f"LSTM input shape expected: {lstm_model.input_shape}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"Error type: {type(e)}")
