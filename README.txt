Project: AI-Driven Forecasting for Efficient Food Supply Chain Management
Phase: Final Delivery
============================================================

1. PROJECT CONTENTS:
----------------------------------------------------------
- app.py (Main Flask Application)
- config.py (Application Configuration)
- feature_engineering.py (Feature Engineering)
- requirements.txt (Python Dependencies)
- models/model_loader.py (ML Model Loader)
- database/db.py (Database Operations)
- utils/helpers.py (Utility Functions)
- templates/ (All HTML Templates)
- data/processed_data.pkl (Preprocessed Training Data)
- data/tuned_models.pkl (All Trained Models)
- data/xgboost_only.pkl (XGBoost Model Only)
- uploads/ (Uploaded Files Directory)


2. SYSTEM REQUIREMENTS:
----------------------------------------------------------
- Operating System: Windows 10/11, macOS, or Linux
- Python Version: 3.11.1 (Recommended)
- RAM: 8GB Minimum (16GB Recommended)
- Storage: 2GB Free Space


3. INSTALLATION STEPS:
----------------------------------------------------------

STEP 1: Extract Project to Short Path (Important for Windows)
        GOOD: D:\Final Application\
        GOOD: C:\Final Application\
        AVOID: Very long nested paths (causes DLL errors)

STEP 2: Open Application folder in Visual Studio

STEP 3: Set Up Python Environment
        When you open the project for the first time,
        an InfoBar appears at the top of the editor prompting you to create a virtual environment and install dependencies from requirements.txt.
        Click "Create virtual environment" or "Install" to proceed.

STEP 4: Install Dependencies (Optional - if Visual Studio does not set up python environment automatically)
        python -m pip install --upgrade pip
        pip install -r requirements.txt

STEP 5: Verify Installation
        python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__)"
        python -c "import xgboost as xgb; print('XGBoost:', xgb.__version__)"
        
        Expected Output:
        TensorFlow: 2.19.0
        XGBoost: 3.2.0


4. RUNNING THE APPLICATION:
----------------------------------------------------------

STEP 1: Start the Application
        python app.py

STEP 2: Open Web Browser
        Go to: http://localhost:5000

STEP 3: Create Account
        - Click "Sign Up"
        - Fill in your details
        - Create account

STEP 4: Login
        - Use your email and password


5. USING THE APPLICATION:
----------------------------------------------------------

A. UPLOAD DATA
   - Navigate to: Data Management
   - Click: Upload Data
   - Select: CSV file with format (week, center_id, meal_id, checkout_price, base_price, emailer_for_promotion, homepage_featured)
   - Sample data files are provided in the project "uploads" folder. Use provided test.csv(32574 rows) file or test_Small.csv(499 rows)
   - If you want quick prediction results then use the test_Small.csv having 499 rows only


B. RUN FORECAST
   - Navigate to: Forecasting
   - Select any Model: XGBoost (Recommended)
   - Choose File: Select uploaded file
   - Click: Run Forecast
   - Wait: 5-10 seconds for processing

C. VIEW RESULTS
   - Navigate to: Dashboard
   - View: 7-Day Forecast Chart
   - Hover: Over bars to see exact numbers
   - Export: Click "Export Chart" to save as PNG

D. MANAGE INVENTORY (Optional)
   - Navigate to: Inventory
   - Add items with current stock levels
   - Set reorder points


6. FILE FORMAT REQUIREMENTS:
----------------------------------------------------------

Supported Formats:
- CSV (.csv)
- Excel (.xlsx, .xls)
- JSON (.json)

Required Columns (for prediction upload):
- week (numeric: 1-52)
- center_id (numeric: restaurant/center identifier)
- meal_id (numeric: menu item identifier)
- checkout_price (numeric: selling price)
- base_price (numeric: original/base price)
- emailer_for_promotion (0 or 1: whether promotion email was sent)
- homepage_featured (0 or 1: whether featured on homepage)

Sample CSV Format (for uploading to make predictions):
week,center_id,meal_id,checkout_price,base_price,emailer_for_promotion,homepage_featured

Sample files are provided in the project "uploads" folder for testing.


7. TROUBLESHOOTING:
----------------------------------------------------------

Issue 1: "DLL load failed" / "Path too long"
Solution: Move project to shorter path (e.g., D:\FoodForecast\)

Issue 2: "Module not found"
Solution: pip install -r requirements.txt --force-reinstall

Issue 3: "Database is locked"
Solution: Wait a few seconds and refresh the page

Issue 4: "File too large"
Solution: Files must be under 100MB

Issue 5: Port 5000 already in use
Solution: python app.py --port=5001


8. IMPORTANT NOTES:
----------------------------------------------------------

DO NOT DELETE:
   - data/processed_data.pkl
   - data/tuned_models.pkl
   - data/xgboost_only.pkl
   - database/food_forecast.db (auto-created)

Sample Data Files:
   - Provided CSV files can be uploaded through Data Management
   - If already uploaded, no need to upload again

First Run:
   - Database auto-creates on first run
   - Takes 10-15 seconds to load models

Dark Mode:
   - Click moon/sun icon in top-right corner
   - Preference saves automatically


9. CONTACT & SUPPORT:
----------------------------------------------------------

For issues during setup or demonstration:
- Check logs/app.log for errors
- Verify Python version is 3.11.1
- Ensure project is in short path (no spaces if possible)
- All models are pre-trained, no training needed

============================================================
Supervisor Name: Dr. Said Nabi
Project By: Faizan Iqbal (BC240213800)
Group Id: F25PROJECTA3E2D 
Course: Final Year Project
Date: April 2026
============================================================


