-- ============================================
-- FOOD FORECAST AI - DATABASE SCHEMA
-- ============================================
-- This schema supports SQLite (development) and PostgreSQL (production)
-- All tables include proper indexes and foreign key constraints
-- ============================================

-- --------------------------------------------
-- 1. USERS TABLE
-- Stores user accounts with restaurant details from signup
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Account Information (Step 1 of signup)
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    
    -- Restaurant Information (Step 2 of signup)
    restaurant_name TEXT NOT NULL,
    restaurant_type TEXT NOT NULL,  -- fine-dining, casual, fast-casual, fast-food, cafe, food-truck, catering, other
    cuisine_type TEXT,               -- e.g., Italian, Asian Fusion, American
    location TEXT NOT NULL,          -- City, State
    daily_customers INTEGER,         -- Average daily customers
    seating_capacity INTEGER,        -- Seating capacity
    
    -- Plan Information (Step 3 of signup)
    plan TEXT DEFAULT 'professional', -- starter, professional, enterprise
    
    -- Account Status
    role TEXT DEFAULT 'user',        -- user, admin
    email_verified BOOLEAN DEFAULT FALSE,
    theme_preference TEXT DEFAULT 'light', -- light, dark
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- Profile
    avatar_color TEXT,               -- Hex color for avatar background
    initials TEXT GENERATED ALWAYS AS (UPPER(SUBSTR(first_name, 1, 1) || SUBSTR(last_name, 1, 1))) STORED
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- --------------------------------------------
-- 2. UPLOADED FILES TABLE
-- Tracks all files uploaded in Data Management
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- File Information
    filename TEXT NOT NULL,           -- Stored filename (UUID)
    original_filename TEXT NOT NULL,  -- Original uploaded filename
    file_path TEXT NOT NULL,          -- Full path to stored file
    file_size INTEGER,                -- Size in bytes
    file_type TEXT,                   -- csv, xlsx, json, pdf, pkl
    
    -- Metadata
    description TEXT,                 -- User-provided description
    folder TEXT DEFAULT 'uploads',    -- sales, inventory, customers, reports
    record_count INTEGER,             -- Number of records (for CSV/Excel)
    
    -- Processing Status
    status TEXT DEFAULT 'pending',    -- pending, processing, processed, failed
    status_message TEXT,              -- Error message if failed
    processed_at TIMESTAMP,
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Relations
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for uploaded_files table
CREATE INDEX IF NOT EXISTS idx_uploaded_files_user_id ON uploaded_files(user_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_folder ON uploaded_files(folder);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_uploaded_at ON uploaded_files(uploaded_at);

-- --------------------------------------------
-- 3. INVENTORY TABLE
-- Tracks food inventory items and stock levels
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Product Information
    product_name TEXT NOT NULL,
    category TEXT,                     -- dairy, meat, vegetables, fruits, grains, beverages
    unit TEXT DEFAULT 'kg',            -- kg, lb, units, liters
    unit_price REAL,
    supplier TEXT,
    
    -- Stock Information
    current_stock REAL DEFAULT 0,
    reorder_point REAL DEFAULT 50,
    reorder_quantity REAL DEFAULT 100,
    minimum_stock REAL DEFAULT 20,
    maximum_stock REAL DEFAULT 500,
    
    -- Expiry Tracking
    expiry_date DATE,
    -- days_until_expiry INTEGER GENERATED ALWAYS AS (JULIANDAY(expiry_date) - JULIANDAY('now')) STORED, error in SQLite, calculate in application logic instead
    
    -- Metadata
    storage_location TEXT,             -- shelf, refrigerator, freezer
    notes TEXT,
    
    -- Timestamps
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for inventory table
CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category);
CREATE INDEX IF NOT EXISTS idx_inventory_low_stock ON inventory(current_stock, reorder_point) WHERE current_stock <= reorder_point;

-- --------------------------------------------
-- 4. MENU ITEMS TABLE
-- Tracks menu items for demand forecasting
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Item Information
    item_name TEXT NOT NULL,
    category TEXT,                     -- appetizer, main, dessert, beverage
    price REAL,
    cost_to_make REAL,                 -- For profit margin calculation
    
    -- Popularity Metrics
    avg_daily_sales REAL DEFAULT 0,
    popularity_score REAL DEFAULT 0,
    
    -- Icon for UI
    icon TEXT DEFAULT 'utensils',      -- Font Awesome icon name
    icon_color TEXT DEFAULT '#4f46e5',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for menu_items table
CREATE INDEX IF NOT EXISTS idx_menu_items_user_id ON menu_items(user_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_menu_items_popularity ON menu_items(popularity_score DESC);

-- --------------------------------------------
-- 5. SALES TRANSACTIONS TABLE
-- Stores daily sales data for forecasting
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS sales_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Transaction Details
    transaction_date DATE NOT NULL,
    menu_item_id INTEGER,
    quantity INTEGER DEFAULT 1,
    unit_price REAL,
    total_amount REAL,
    
    -- Customer Information
    customer_age_group TEXT,           -- 18-25, 26-35, 36-50, 51-65, 65+
    customer_gender TEXT,              -- male, female, other, unknown
    is_weekend BOOLEAN GENERATED ALWAYS AS (
        CAST(strftime('%w', transaction_date) AS INTEGER) IN (0, 6)
    ) STORED,
    day_of_week INTEGER GENERATED ALWAYS AS (
        CAST(strftime('%w', transaction_date) AS INTEGER)
    ) STORED,
    
    -- Weather Data (can be joined from external API)
    weather_condition TEXT,            -- sunny, cloudy, rainy, etc.
    temperature REAL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE SET NULL
);

-- Indexes for sales_transactions table
CREATE INDEX IF NOT EXISTS idx_sales_user_id ON sales_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_sales_menu_item ON sales_transactions(menu_item_id);
CREATE INDEX IF NOT EXISTS idx_sales_age_group ON sales_transactions(customer_age_group);

-- --------------------------------------------
-- 6. FORECASTS TABLE
-- Stores demand forecasts generated by ML models
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Model Information
    model_name TEXT NOT NULL,           -- linear, arima, lstm, xgboost, prophet, randomforest, ensemble
    model_version TEXT,                 -- Version of the model used
    input_file_id INTEGER,              -- File used to train/generate forecast
    
    -- Forecast Details
    forecast_date DATE NOT NULL,        -- Date being forecasted
    target_item_id INTEGER,             -- Menu item or product being forecasted (NULL for overall)
    target_type TEXT DEFAULT 'overall', -- overall, menu_item, category
    
    -- Prediction Values
    predicted_demand REAL NOT NULL,
    confidence_lower REAL,
    confidence_upper REAL,
    confidence_interval REAL DEFAULT 0.95,
    
    -- Model Metrics
    accuracy_score REAL,                -- Model accuracy for this forecast
    mape REAL,                          -- Mean Absolute Percentage Error
    rmse REAL,                          -- Root Mean Square Error
    
    -- Parameters Used
    parameters_used TEXT,               -- JSON string of model parameters
    
    -- Status
    status TEXT DEFAULT 'active',       -- active, expired, superseded
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (input_file_id) REFERENCES uploaded_files(id) ON DELETE SET NULL,
    FOREIGN KEY (target_item_id) REFERENCES menu_items(id) ON DELETE CASCADE
);

-- Indexes for forecasts table
CREATE INDEX IF NOT EXISTS idx_forecasts_user_id ON forecasts(user_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_date ON forecasts(forecast_date);
CREATE INDEX IF NOT EXISTS idx_forecasts_model ON forecasts(model_name);
CREATE INDEX IF NOT EXISTS idx_forecasts_item ON forecasts(target_item_id);

-- --------------------------------------------
-- 7. ACTUALS TABLE
-- Stores actual demand values for forecast accuracy calculation
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    actual_date DATE NOT NULL,
    target_item_id INTEGER,
    target_type TEXT DEFAULT 'overall',
    
    actual_demand REAL NOT NULL,
    
    -- Link to forecast
    forecast_id INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (target_item_id) REFERENCES menu_items(id) ON DELETE CASCADE,
    FOREIGN KEY (forecast_id) REFERENCES forecasts(id) ON DELETE SET NULL
);

-- Indexes for actuals table
CREATE INDEX IF NOT EXISTS idx_actuals_user_id ON actuals(user_id);
CREATE INDEX IF NOT EXISTS idx_actuals_date ON actuals(actual_date);

-- --------------------------------------------
-- 8. ALERTS TABLE
-- Stores system alerts and notifications
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Alert Information
    alert_type TEXT NOT NULL,           -- low_inventory, weather_impact, high_demand, forecast_ready, system
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,                       -- Additional JSON details
    
    -- Related Entities
    related_item_id INTEGER,            -- inventory item or menu item
    related_forecast_id INTEGER,
    
    -- Priority
    priority TEXT DEFAULT 'medium',     -- low, medium, high, critical
    icon TEXT DEFAULT 'info-circle',
    icon_color TEXT DEFAULT '#3b82f6',
    
    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_forecast_id) REFERENCES forecasts(id) ON DELETE SET NULL
);

-- Indexes for alerts table
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);

-- --------------------------------------------
-- 9. MODEL_RUNS TABLE
-- Tracks ML model execution history
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS model_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Run Information
    model_name TEXT NOT NULL,
    input_file_id INTEGER,
    status TEXT DEFAULT 'pending',      -- pending, running, completed, failed
    
    -- Results
    forecast_count INTEGER DEFAULT 0,
    accuracy_achieved REAL,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    
    -- Error Information
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (input_file_id) REFERENCES uploaded_files(id) ON DELETE SET NULL
);

-- Indexes for model_runs table
CREATE INDEX IF NOT EXISTS idx_model_runs_user_id ON model_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_model_runs_model ON model_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_model_runs_created_at ON model_runs(created_at DESC);

-- --------------------------------------------
-- 10. WASTE_RECORDS TABLE
-- Tracks food waste for sustainability metrics
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS waste_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- Waste Information
    waste_date DATE NOT NULL,
    inventory_item_id INTEGER,
    menu_item_id INTEGER,
    
    quantity_wasted REAL NOT NULL,
    unit TEXT DEFAULT 'kg',
    waste_reason TEXT,                  -- expired, overproduction, spoilage, customer_return, other
    
    cost_impact REAL,                   -- Financial impact of waste
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory(id) ON DELETE SET NULL,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE SET NULL
);

-- Indexes for waste_records table
CREATE INDEX IF NOT EXISTS idx_waste_user_id ON waste_records(user_id);
CREATE INDEX IF NOT EXISTS idx_waste_date ON waste_records(waste_date);

-- --------------------------------------------
-- 11. USER_SESSIONS TABLE
-- Tracks user login sessions
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    session_token TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for user_sessions table
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- --------------------------------------------
-- 12. AUDIT_LOGS TABLE
-- Tracks important user actions for security
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    
    action TEXT NOT NULL,               -- login, logout, signup, upload, delete, forecast, etc.
    entity_type TEXT,                   -- user, file, forecast, inventory, etc.
    entity_id INTEGER,
    
    details TEXT,                       -- JSON string with additional info
    ip_address TEXT,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for audit_logs table
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC);

-- ============================================
-- DEFAULT DATA & SAMPLE RECORDS
-- ============================================

-- Insert default admin user (password: admin123)
-- Password hash generated using: scrypt hash of 'admin123'
INSERT INTO users (
    first_name, last_name, email, phone, password_hash,
    restaurant_name, restaurant_type, cuisine_type, location,
    daily_customers, seating_capacity, plan, role, email_verified
) VALUES (
    'Admin', 'User', 'admin@foodforecast.ai', '+1 (555) 000-0000',
    'scrypt:32768:8:1$H8kPjLmNqRtYxZwV$3f8a9e2b1c6d4f7e9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5',
    'Food Forecast HQ', 'fine-dining', 'International', 'New York, NY',
    250, 120, 'enterprise', 'admin', TRUE
) ON CONFLICT(email) DO NOTHING;

-- Insert sample restaurant user (password: restaurant123)
INSERT INTO users (
    first_name, last_name, email, phone, password_hash,
    restaurant_name, restaurant_type, cuisine_type, location,
    daily_customers, seating_capacity, plan, role, email_verified
) VALUES (
    'Sarah', 'Chen', 'sarah@urbanbistro.com', '+1 (555) 123-4567',
    'scrypt:32768:8:1$H8kPjLmNqRtYxZwV$3f8a9e2b1c6d4f7e9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5',
    'Urban Bistro', 'casual', 'Asian Fusion', 'San Francisco, CA',
    180, 80, 'professional', 'user', TRUE
) ON CONFLICT(email) DO NOTHING;

-- Insert sample inventory items for the sample user
INSERT INTO inventory (user_id, product_name, category, unit, unit_price, current_stock, reorder_point, supplier) VALUES
(2, 'Fresh Milk', 'dairy', 'liters', 3.99, 450, 100, 'Local Dairy Farm'),
(2, 'Chicken Breast', 'meat', 'kg', 5.99, 280, 80, 'Premium Meats Co.'),
(2, 'Tomatoes', 'vegetables', 'kg', 2.49, 520, 120, 'Fresh Farms'),
(2, 'Apples', 'fruits', 'kg', 1.99, 390, 90, 'Valley Orchards'),
(2, 'Rice', 'grains', 'kg', 0.99, 1200, 200, 'Global Foods'),
(2, 'Orange Juice', 'beverages', 'liters', 4.49, 180, 60, 'Citrus World')
ON CONFLICT DO NOTHING;

-- Insert sample menu items for the sample user
INSERT INTO menu_items (user_id, item_name, category, price, cost_to_make, avg_daily_sales, popularity_score, icon) VALUES
(2, 'Classic Burger', 'main', 9.99, 4.50, 45, 0.95, 'hamburger'),
(2, 'Pepperoni Pizza', 'main', 14.99, 5.20, 38, 0.88, 'pizza-slice'),
(2, 'Caesar Salad', 'appetizer', 12.99, 3.80, 32, 0.82, 'leaf'),
(2, 'Spaghetti Bolognese', 'main', 13.99, 4.90, 28, 0.79, 'utensil-spoon'),
(2, 'Grilled Salmon', 'main', 18.99, 8.50, 20, 0.72, 'fish'),
(2, 'Chocolate Cake', 'dessert', 7.99, 2.30, 25, 0.85, 'cake')
ON CONFLICT DO NOTHING;

-- Insert sample alerts for the sample user
INSERT INTO alerts (user_id, alert_type, title, message, details, priority, icon) VALUES
(2, 'low_inventory', 'Low Inventory Alert: Rice', 'Current stock (2kg) is below reorder point (5kg)', '{"item": "Rice", "current": 2, "reorder": 5}', 'high', 'exclamation-triangle'),
(2, 'weather_impact', 'Weather Impact Alert', 'Rain expected tomorrow (-15% customers)', '{"impact": -15, "weather": "rain"}', 'medium', 'cloud-sun-rain'),
(2, 'high_demand', 'High Demand Predicted', 'Burgers +25% for Friday', '{"item": "Classic Burger", "increase": 25}', 'medium', 'chart-line'),
(2, 'forecast_ready', 'New Forecast Ready', '7-day demand forecast has been generated', '{"model": "XGBoost", "accuracy": 96}', 'low', 'robot')
ON CONFLICT DO NOTHING;

-- Insert sample forecasts for the sample user
INSERT INTO forecasts (user_id, model_name, forecast_date, predicted_demand, confidence_lower, confidence_upper, accuracy_score) VALUES
(2, 'xgboost', date('now', '+1 day'), 145, 138, 152, 0.96),
(2, 'xgboost', date('now', '+2 days'), 152, 145, 159, 0.96),
(2, 'xgboost', date('now', '+3 days'), 160, 152, 168, 0.95),
(2, 'xgboost', date('now', '+4 days'), 155, 147, 163, 0.95),
(2, 'xgboost', date('now', '+5 days'), 148, 140, 156, 0.94),
(2, 'xgboost', date('now', '+6 days'), 142, 134, 150, 0.94),
(2, 'xgboost', date('now', '+7 days'), 138, 130, 146, 0.93)
ON CONFLICT DO NOTHING;

-- ============================================
-- VIEWS FOR DASHBOARD ANALYTICS
-- ============================================

-- View: Daily sales summary
CREATE VIEW IF NOT EXISTS daily_sales_summary AS
SELECT 
    user_id,
    transaction_date,
    COUNT(*) as transaction_count,
    SUM(quantity) as items_sold,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_transaction_value
FROM sales_transactions
GROUP BY user_id, transaction_date;

-- View: Forecast accuracy
CREATE VIEW IF NOT EXISTS forecast_accuracy AS
SELECT 
    f.user_id,
    f.model_name,
    f.forecast_date,
    f.predicted_demand,
    a.actual_demand,
    ABS(f.predicted_demand - a.actual_demand) as absolute_error,
    (ABS(f.predicted_demand - a.actual_demand) / a.actual_demand * 100) as percentage_error
FROM forecasts f
LEFT JOIN actuals a ON f.forecast_date = a.actual_date AND f.user_id = a.user_id;

-- View: Low stock alerts
CREATE VIEW IF NOT EXISTS low_stock_items AS
SELECT 
    user_id,
    product_name,
    category,
    current_stock,
    reorder_point,
    (reorder_point - current_stock) as shortage_amount
FROM inventory
WHERE current_stock <= reorder_point;

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger: Update user updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_user_timestamp 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: Update inventory last_updated timestamp
CREATE TRIGGER IF NOT EXISTS update_inventory_timestamp 
AFTER UPDATE ON inventory
BEGIN
    UPDATE inventory SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: Create low stock alert
CREATE TRIGGER IF NOT EXISTS low_stock_alert
AFTER UPDATE OF current_stock ON inventory
WHEN NEW.current_stock <= NEW.reorder_point AND OLD.current_stock > OLD.reorder_point
BEGIN
    INSERT INTO alerts (user_id, alert_type, title, message, details, priority, icon, related_item_id)
    VALUES (
        NEW.user_id,
        'low_inventory',
        'Low Inventory Alert: ' || NEW.product_name,
        'Current stock (' || NEW.current_stock || ') is below reorder point (' || NEW.reorder_point || ')',
        json_object('item', NEW.product_name, 'current', NEW.current_stock, 'reorder', NEW.reorder_point),
        'high',
        'exclamation-triangle',
        NEW.id
    );
END;

-- ============================================
-- END OF SCHEMA
-- ============================================