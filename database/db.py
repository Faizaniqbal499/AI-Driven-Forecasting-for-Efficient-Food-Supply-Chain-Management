"""
Database connection and query functions for Food Forecast AI.
Supports both SQLite (development) and PostgreSQL (production).
"""

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
import time

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

# Get configuration
config = get_config()

def get_display_filename(stored_filename):
    """Extract original filename from stored filename (removes UUID prefix)"""
    if '_' in stored_filename and len(stored_filename.split('_')[0]) == 32:  # UUID is 32 chars
        return stored_filename.split('_', 1)[1]
    return stored_filename

# ============================================
# DATABASE CONNECTION
# ============================================

def get_db_connection():
    """
    Get a database connection based on configuration.
    Returns SQLite connection for development, PostgreSQL for production.
    """
    db_url = config.DATABASE_URL
    
    if db_url.startswith('sqlite:///'):
        # SQLite connection
        db_path = db_url.replace('sqlite:///', '')
        
        # Ensure the instance directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Add timeout parameter here - wait up to 20 seconds for lock
        conn = sqlite3.connect(db_path, timeout=20)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        
        # Enable foreign keys
        conn.execute('PRAGMA foreign_keys = ON')
        
        return conn
    else:
        # PostgreSQL connection (for production)
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(db_url)
        return conn


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_cursor(conn):
    """
    Get a cursor appropriate for the database type.
    For SQLite, returns standard cursor.
    For PostgreSQL, returns RealDictCursor.
    """
    if isinstance(conn, sqlite3.Connection):
        return conn.cursor()
    else:
        return conn.cursor(cursor_factory=RealDictCursor)


# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_db():
    """
    Initialize the database by running schema.sql.
    Creates all tables if they don't exist.
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Use utf-8-sig encoding to handle BOM automatically
        with open(schema_path, 'r', encoding='utf-8-sig') as f:
            schema_sql = f.read()
            
        # SQLite doesn't support multiple statements in one execute
        if isinstance(conn, sqlite3.Connection):
            cursor.executescript(schema_sql)
        else:
            cursor.execute(schema_sql)
        
        print("Database initialized successfully!")


def reset_db():
    """
    WARNING: Drops all tables and recreates them.
    Only for development use!
    """
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError("Cannot reset database in production!")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if isinstance(conn, sqlite3.Connection):
            # Drop all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                if table['name'] != 'sqlite_sequence':
                    cursor.execute(f"DROP TABLE IF EXISTS {table['name']}")
        else:
            # PostgreSQL
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = cursor.fetchall()
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table['tablename']} CASCADE")
    
    # Reinitialize
    init_db()
    print("Database reset successfully!")


# ============================================
# USER OPERATIONS
# ============================================

def create_user(user_data: Dict[str, Any]) -> int:
    """
    Create a new user from signup form data.
    
    Args:
        user_data: Dictionary containing user registration data
        
    Returns:
        int: ID of the newly created user
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (
                first_name, last_name, email, phone, password_hash,
                restaurant_name, restaurant_type, cuisine_type, location,
                daily_customers, seating_capacity, plan, role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_data.get('first_name'),
            user_data.get('last_name'),
            user_data.get('email'),
            user_data.get('phone'),
            user_data.get('password_hash'),
            user_data.get('restaurant_name'),
            user_data.get('restaurant_type'),
            user_data.get('cuisine_type'),
            user_data.get('location'),
            user_data.get('daily_customers'),
            user_data.get('seating_capacity'),
            user_data.get('plan', 'professional'),
            'user'
        ))
        
        return cursor.lastrowid


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address.
    
    Args:
        email: User's email address
        
    Returns:
        Dict containing user data or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by ID.
    
    Args:
        user_id: User's ID
        
    Returns:
        Dict containing user data or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user(user_id: int, updates: Dict[str, Any]) -> bool:
    """
    Update user information.
    
    Args:
        user_id: User's ID
        updates: Dictionary of fields to update
        
    Returns:
        bool: True if successful
    """
    allowed_fields = [
        'first_name', 'last_name', 'phone', 'restaurant_name',
        'restaurant_type', 'cuisine_type', 'location',
        'daily_customers', 'seating_capacity', 'plan',
        'theme_preference', 'email_verified'
    ]
    
    set_clauses = []
    values = []
    
    for field, value in updates.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = ?")
            values.append(value)
    
    if not set_clauses:
        return False
    
    values.append(user_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE users 
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, values)
        
        return cursor.rowcount > 0


def update_last_login(user_id: int) -> None:
    """Update user's last login timestamp."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (user_id,))


def update_theme_preference(user_id: int, theme: str) -> None:
    """Update user's theme preference."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET theme_preference = ? 
            WHERE id = ?
        """, (theme, user_id))


# ============================================
# FILE OPERATIONS
# ============================================

def save_uploaded_file(user_id: int, file_data: Dict[str, Any]) -> int:
    """
    Save uploaded file metadata to database with retry on lock.
    
    Args:
        user_id: ID of the user uploading the file
        file_data: Dictionary with filename, original_filename, file_path, etc.
        
    Returns:
        int: ID of the saved file record
    """
    import time
    
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Determine folder based on filename/content
                folder = determine_folder(file_data.get('original_filename', ''))
                
                cursor.execute("""
                    INSERT INTO uploaded_files (
                        user_id, filename, original_filename, file_path,
                        file_size, file_type, folder, description, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    file_data.get('filename'),
                    file_data.get('original_filename'),
                    file_data.get('file_path'),
                    file_data.get('file_size'),
                    file_data.get('file_type'),
                    folder,
                    file_data.get('description', ''),
                    'pending'
                ))
                
                file_id = cursor.lastrowid
            
            # Log audit in a SEPARATE connection to avoid lock
            try:
                log_audit(user_id, 'upload', 'file', file_id, 
                          f"Uploaded {file_data.get('original_filename')}")
            except Exception as audit_error:
                print(f"Warning: Could not log audit: {audit_error}")
            
            return file_id
            
        except Exception as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise e


def determine_folder(filename: str) -> str:
    """Determine folder based on filename keywords."""
    filename_lower = filename.lower()
    
    if any(kw in filename_lower for kw in ['sale', 'transaction', 'revenue']):
        return 'sales'
    elif any(kw in filename_lower for kw in ['inventory', 'stock', 'supply']):
        return 'inventory'
    elif any(kw in filename_lower for kw in ['customer', 'demo', 'age']):
        return 'customers'
    elif any(kw in filename_lower for kw in ['report', 'waste', 'analysis']):
        return 'reports'
    else:
        return 'uploads'


def get_user_files(user_id: int, folder: Optional[str] = None, 
                   status: Optional[str] = None,
                   limit: int = 10, offset: int = 0,
                   search: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get files uploaded by a user with optional filtering.
    
    Returns:
        Tuple of (files list, total count)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_clauses = ["user_id = ?"]
        params = [user_id]
        
        if folder:
            where_clauses.append("folder = ?")
            params.append(folder)
        
        # FIX: Only add status filter if status is provided (not None)
        if status is not None:  # Changed from 'if status' to 'if status is not None'
            where_clauses.append("status = ?")
            params.append(status)
            
        if search:
            where_clauses.append("(original_filename LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_sql = " AND ".join(where_clauses)
        
        # Get total count
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM uploaded_files 
            WHERE {where_sql}
        """, params)
        total = cursor.fetchone()['count']
        
        # Get files with pagination
        cursor.execute(f"""
            SELECT 
                id, filename, original_filename, file_size, file_type,
                folder, status, description, uploaded_at, processed_at,
                CASE 
                    WHEN status = 'pending' THEN 'Pending'
                    WHEN status = 'processing' THEN 'Processing'
                    WHEN status = 'processed' THEN 'Processed'
                    WHEN status = 'failed' THEN 'Failed'
                    ELSE status
                END as status_text,
                CASE 
                    WHEN file_type = 'csv' THEN 'csv'
                    WHEN file_type IN ('xlsx', 'xls') THEN 'xlsx'
                    WHEN file_type = 'json' THEN 'json'
                    WHEN file_type = 'pdf' THEN 'pdf'
                    ELSE 'csv'
                END as icon_class,
                CASE 
                    WHEN file_type = 'csv' THEN 'file-csv'
                    WHEN file_type IN ('xlsx', 'xls') THEN 'file-excel'
                    WHEN file_type = 'json' THEN 'file-code'
                    WHEN file_type = 'pdf' THEN 'file-pdf'
                    ELSE 'file-alt'
                END as icon,
                DATE(uploaded_at) as upload_date
            FROM uploaded_files 
            WHERE {where_sql}
            ORDER BY uploaded_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        files = [dict(row) for row in cursor.fetchall()]
        
        # Format file sizes and add display name
        for file in files:
            if file.get('file_size'):
                file['file_size'] = format_file_size(file['file_size'])
            
            # Create a clean display name without UUID prefix
            original_filename = file.get('original_filename', '')
            if original_filename and '_' in original_filename:
                # Check if the prefix is a UUID (32 characters of hex)
                parts = original_filename.split('_', 1)
                if len(parts) == 2 and len(parts[0]) == 32 and all(c in '0123456789abcdef' for c in parts[0].lower()):
                    file['display_name'] = parts[1]
                else:
                    file['display_name'] = original_filename
            else:
                file['display_name'] = original_filename
        
        return files, total


def format_file_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    if bytes == 0:
        return '0 Bytes'
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB']
    i = 0
    while bytes >= k and i < len(sizes) - 1:
        bytes /= k
        i += 1
    return f"{bytes:.1f} {sizes[i]}"


def get_file_by_id(file_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get file by ID, optionally checking ownership."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT * FROM uploaded_files 
                WHERE id = ? AND user_id = ?
            """, (file_id, user_id))
        else:
            cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
            
        row = cursor.fetchone()
        return dict(row) if row else None


def update_file_status(file_id: int, status: str, status_message: Optional[str] = None) -> None:
    """Update file processing status."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if status == 'processed':
            cursor.execute("""
                UPDATE uploaded_files 
                SET status = ?, status_message = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, status_message, file_id))
        else:
            cursor.execute("""
                UPDATE uploaded_files 
                SET status = ?, status_message = ?
                WHERE id = ?
            """, (status, status_message, file_id))


def delete_file(file_id: int, user_id: int) -> bool:
    """
    Delete a file record (and optionally the physical file).
    Returns True if successful.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get file path first
        cursor.execute("""
            SELECT file_path FROM uploaded_files 
            WHERE id = ? AND user_id = ?
        """, (file_id, user_id))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        file_path = row['file_path']
        
        # Delete from database
        cursor.execute("""
            DELETE FROM uploaded_files 
            WHERE id = ? AND user_id = ?
        """, (file_id, user_id))
        
        # Try to delete physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass  # File might be in use or already deleted
        
        # Log the action
        log_audit(user_id, 'delete', 'file', file_id, f"Deleted file")
        
        return cursor.rowcount > 0


# ============================================
# DASHBOARD OPERATIONS
# ============================================

def get_dashboard_stats(user_id: int) -> Dict[str, Any]:
    """
    Get dashboard statistics for a user.
    """
    stats = {
        'today_customers': 0,
        'customers_trend': 0,
        'forecast_accuracy': 92,
        'accuracy_trend': 3,
        'daily_waste': 4.2,
        'waste_trend': -12,
        'today_revenue': 2845,
        'revenue_trend': 8,
        'sales_records': 0,
        'records_trend': 12,
        'menu_items': 0,
        'items_trend': 5,
        'waste_reports': 0,
        'total_storage': '0 GB',
        'storage_trend': 3
    }
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Today's customers (placeholder - would come from actual sales data)
        cursor.execute("""
            SELECT COUNT(DISTINCT id) as count 
            FROM sales_transactions 
            WHERE user_id = ? AND transaction_date = DATE('now')
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            stats['today_customers'] = row['count'] or 142
        
        # Sales records count
        cursor.execute("""
            SELECT COUNT(*) as count FROM uploaded_files 
            WHERE user_id = ? AND folder = 'sales'
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            stats['sales_records'] = row['count'] or 1247
        
        # Menu items count
        cursor.execute("""
            SELECT COUNT(*) as count FROM menu_items 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            stats['menu_items'] = row['count'] or 892
        
        # Waste reports count
        cursor.execute("""
            SELECT COUNT(*) as count FROM waste_records 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            stats['waste_reports'] = row['count'] or 142
        
        # Total storage used
        cursor.execute("""
            SELECT SUM(file_size) as total FROM uploaded_files 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row and row['total']:
            stats['total_storage'] = format_file_size(row['total'])
    
    return stats


def get_folder_stats(user_id: int) -> List[Dict[str, Any]]:
    """Get folder statistics for data management page."""
    folders = [
        {'name': 'Sales Data', 'icon': 'chart-line', 'icon_class': 'sales', 'folder': 'sales'},
        {'name': 'Inventory', 'icon': 'box', 'icon_class': 'inventory', 'folder': 'inventory'},
        {'name': 'Customer Demographics', 'icon': 'users', 'icon_class': 'customers', 'folder': 'customers'},
        {'name': 'Reports', 'icon': 'file-pdf', 'icon_class': 'reports', 'folder': 'reports'}
    ]
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for folder in folders:
            cursor.execute("""
                SELECT COUNT(*) as count, SUM(file_size) as total_size
                FROM uploaded_files 
                WHERE folder = ?
            """, (folder['folder'],))
            
            row = cursor.fetchone()
            folder['file_count'] = row['count'] if row else 0
            folder['size'] = format_file_size(row['total_size']) if row and row['total_size'] else '0 MB'
            folder['id'] = folders.index(folder) + 1
    
    return folders


def get_top_menu_items(user_id: int, limit: int = 4) -> List[Dict[str, Any]]:
    """Get top menu items for dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, item_name as name, price, icon, avg_daily_sales as sold,
                CASE 
                    WHEN category = 'main' THEN 'burger'
                    WHEN category = 'appetizer' THEN 'salad'
                    WHEN category = 'dessert' THEN 'cake'
                    ELSE 'utensils'
                END as icon_class
            FROM menu_items 
            WHERE user_id = ? AND is_active = 1
            ORDER BY popularity_score DESC
            LIMIT ?
        """, (user_id, limit))
        
        items = [dict(row) for row in cursor.fetchall()]
        
        # Map icon classes
        icon_map = {
            'burger': 'burger',
            'pizza-slice': 'pizza',
            'leaf': 'salad',
            'utensil-spoon': 'pasta'
        }
        
        for item in items:
            item['icon_class'] = icon_map.get(item.get('icon', 'utensils'), 'burger')
            
        return items


def get_alerts(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent alerts for dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, alert_type as type, title, message as details,
                priority, icon, resolved,
                CASE 
                    WHEN resolved THEN 'noted'
                    WHEN priority = 'high' THEN 'action'
                    ELSE 'noted'
                END as status_class,
                CASE 
                    WHEN resolved THEN 'Resolved'
                    WHEN priority = 'high' THEN 'Action Required'
                    WHEN priority = 'medium' THEN 'Noted'
                    ELSE 'Planned'
                END as status_text,
                CASE 
                    WHEN alert_type = 'low_inventory' THEN 'warning'
                    WHEN alert_type = 'weather_impact' THEN 'weather'
                    ELSE 'info'
                END as icon_class,
                DATE(created_at) as created_date
            FROM alerts 
            WHERE user_id = ? AND resolved = 0
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END,
                created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]


def get_forecast_data(user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Get forecast data for chart."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get forecasts for the next 'days' days - ONE PER DAY
        cursor.execute("""
            SELECT DISTINCT
                forecast_date,
                predicted_demand as predicted,
                CAST(strftime('%w', forecast_date) AS INTEGER) as day_num,
                CASE CAST(strftime('%w', forecast_date) AS INTEGER)
                    WHEN 0 THEN 'Sun'
                    WHEN 1 THEN 'Mon'
                    WHEN 2 THEN 'Tue'
                    WHEN 3 THEN 'Wed'
                    WHEN 4 THEN 'Thu'
                    WHEN 5 THEN 'Fri'
                    WHEN 6 THEN 'Sat'
                END as day
            FROM forecasts 
            WHERE user_id = ? 
            AND forecast_date >= DATE('now')
            AND forecast_date <= DATE('now', '+' || ? || ' days')
            GROUP BY forecast_date
            ORDER BY forecast_date
            LIMIT ?
        """, (user_id, days, days))
        
        forecasts = [dict(row) for row in cursor.fetchall()]
        
        # If no forecasts found, get the most recent ones
        if not forecasts:
            cursor.execute("""
                SELECT DISTINCT
                    forecast_date,
                    predicted_demand as predicted,
                    CAST(strftime('%w', forecast_date) AS INTEGER) as day_num,
                    CASE CAST(strftime('%w', forecast_date) AS INTEGER)
                        WHEN 0 THEN 'Sun'
                        WHEN 1 THEN 'Mon'
                        WHEN 2 THEN 'Tue'
                        WHEN 3 THEN 'Wed'
                        WHEN 4 THEN 'Thu'
                        WHEN 5 THEN 'Fri'
                        WHEN 6 THEN 'Sat'
                    END as day
                FROM forecasts 
                WHERE user_id = ? 
                GROUP BY forecast_date
                ORDER BY forecast_date DESC
                LIMIT ?
            """, (user_id, days))
            forecasts = [dict(row) for row in cursor.fetchall()]
            forecasts.reverse()  # Put in ascending order
        
        # Add sample actual data (since you don't have actuals yet)
        import random
        for fc in forecasts:
            # Generate actual values slightly different from predicted
            predicted = fc['predicted']
            variation = random.uniform(0.92, 1.08)
            fc['actual'] = int(predicted * variation)
        
        return forecasts


def get_age_distribution(user_id: int) -> List[Dict[str, Any]]:
    """Get customer age distribution."""
    age_groups = [
        {'range': '18-25', 'min': 18, 'max': 25, 'color': '#3b82f6'},
        {'range': '26-35', 'min': 26, 'max': 35, 'color': '#10b981'},
        {'range': '36-50', 'min': 36, 'max': 50, 'color': '#f59e0b'},
        {'range': '51-65', 'min': 51, 'max': 65, 'color': '#ef4444'},
        {'range': '65+', 'min': 65, 'max': 999, 'color': '#8b5cf6'}
    ]
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for group in age_groups:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM sales_transactions 
                WHERE user_id = ? 
                AND customer_age_group = ?
            """, (user_id, group['range']))
            
            row = cursor.fetchone()
            group['count'] = row['count'] if row else 0
        
        # Calculate percentages
        total = sum(g['count'] for g in age_groups)
        if total > 0:
            for group in age_groups:
                group['percentage'] = round((group['count'] / total) * 100)
        else:
            # Default distribution if no data
            defaults = [32, 28, 22, 12, 6]
            for i, group in enumerate(age_groups):
                group['percentage'] = defaults[i]
        
        return age_groups


# ============================================
# FORECAST OPERATIONS
# ============================================

def save_forecast(user_id: int, forecast_data: Dict[str, Any]) -> int:
    """
    Save a forecast result to the database.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO forecasts (
                user_id, model_name, forecast_date, predicted_demand,
                confidence_lower, confidence_upper, confidence_interval,
                accuracy_score, parameters_used, input_file_id, target_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            forecast_data.get('model_name'),
            forecast_data.get('forecast_date'),
            forecast_data.get('predicted_demand'),
            forecast_data.get('confidence_lower'),
            forecast_data.get('confidence_upper'),
            forecast_data.get('confidence_interval', 0.95),
            forecast_data.get('accuracy_score'),
            forecast_data.get('parameters_used'),
            forecast_data.get('input_file_id'),
            forecast_data.get('target_type', 'overall')
        ))
        
        return cursor.lastrowid


def get_recent_models(user_id: int, limit: int = 4) -> List[Dict[str, Any]]:
    """Get recently used models for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT 
                model_name,
                MAX(created_at) as last_used
            FROM forecasts 
            WHERE user_id = ?
            GROUP BY model_name
            ORDER BY last_used DESC
            LIMIT ?
        """, (user_id, limit))
        
        recent = []
        model_configs = config.AVAILABLE_MODELS
        
        for row in cursor.fetchall():
            model_name = row['model_name']
            if model_name in model_configs:
                model = model_configs[model_name].copy()
                
                # Format last used time
                last_used = datetime.strptime(row['last_used'][:19], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                diff = now - last_used
                
                if diff.days == 0:
                    if diff.seconds < 3600:
                        model['last_used'] = f"{diff.seconds // 60} minutes ago"
                    else:
                        model['last_used'] = f"{diff.seconds // 3600} hours ago"
                elif diff.days == 1:
                    model['last_used'] = "yesterday"
                elif diff.days < 7:
                    model['last_used'] = f"{diff.days} days ago"
                else:
                    model['last_used'] = "last week"
                
                recent.append(model)
        
        return recent


def create_model_run(user_id: int, model_name: str, input_file_id: Optional[int] = None) -> int:
    """Create a new model run record."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO model_runs (
                user_id, model_name, input_file_id, status, started_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, model_name, input_file_id, 'running'))
        
        return cursor.lastrowid


def update_model_run(run_id: int, status: str, results: Optional[Dict[str, Any]] = None) -> None:
    """Update model run status and results."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if status == 'completed':
            cursor.execute("""
                UPDATE model_runs 
                SET status = ?, 
                    completed_at = CURRENT_TIMESTAMP,
                    forecast_count = ?,
                    accuracy_achieved = ?
                WHERE id = ?
            """, (
                status,
                results.get('forecast_count', 0) if results else 0,
                results.get('accuracy_achieved') if results else None,
                run_id
            ))
        elif status == 'failed':
            cursor.execute("""
                UPDATE model_runs 
                SET status = ?, 
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = ?
                WHERE id = ?
            """, (status, results.get('error') if results else None, run_id))
        else:
            cursor.execute("""
                UPDATE model_runs SET status = ? WHERE id = ?
            """, (status, run_id))


# ============================================
# AUDIT LOGGING
# ============================================

def log_audit(user_id: int, action: str, entity_type: str, 
              entity_id: int, details: Optional[str] = None,
              ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    """
    Log an audit event with its own connection.
    """
      
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Use a separate connection for audit logging
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (
                        user_id, action, entity_type, entity_id, details, ip_address, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, action, entity_type, entity_id, details, ip_address, user_agent))
            return
        except Exception as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                time.sleep(0.3)
                continue
            # Silently fail audit logging - don't crash main operation
            print(f"Audit log failed: {e}")
            return


# ============================================
# SESSION MANAGEMENT
# ============================================

def create_session(user_id: int, session_token: str, expires_at: datetime,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    """Create a new user session."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions (
                user_id, session_token, ip_address, user_agent, expires_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, session_token, ip_address, user_agent, expires_at))


def validate_session(session_token: str) -> Optional[Dict[str, Any]]:
    """Validate a session token and return user if valid."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.* 
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? 
            AND s.is_active = 1
            AND s.expires_at > CURRENT_TIMESTAMP
            AND u.is_active = 1
        """, (session_token,))
        
        row = cursor.fetchone()
        
        if row:
            # Update last activity
            cursor.execute("""
                UPDATE user_sessions 
                SET last_activity = CURRENT_TIMESTAMP
                WHERE session_token = ?
            """, (session_token,))
            
            return dict(row)
        
        return None


def invalidate_session(session_token: str) -> None:
    """Invalidate a session (logout)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions SET is_active = 0 WHERE session_token = ?
        """, (session_token,))


def cleanup_expired_sessions() -> int:
    """Clean up expired sessions. Returns number of sessions cleaned."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions SET is_active = 0 
            WHERE expires_at < CURRENT_TIMESTAMP AND is_active = 1
        """)
        return cursor.rowcount


# ============================================
# UTILITY FUNCTIONS
# ============================================

def row_to_dict(row) -> Dict[str, Any]:
    """Convert a database row to a dictionary."""
    if row is None:
        return None
    
    if isinstance(row, dict):
        return row
    
    if hasattr(row, 'keys'):
        return {key: row[key] for key in row.keys()}
    
    return dict(row)


# ============================================
# MODULE INITIALIZATION
# ============================================

# Create database/db.py
if __name__ == '__main__':
    print("Database module for Food Forecast AI")
    print(f"Database URL: {config.DATABASE_URL}")


# ============================================
# INVENTORY PLANNING FUNCTIONS
# ============================================

def get_inventory_items(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get current inventory items with CORRECT status logic."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, product_name, category, unit, unit_price,
                current_stock, reorder_point, minimum_stock,
                supplier, storage_location, expiry_date,
                CASE 
                    WHEN current_stock <= minimum_stock THEN 'critical'
                    WHEN current_stock <= reorder_point THEN 'low'
                    ELSE 'normal'
                END as stock_status
            FROM inventory 
            WHERE user_id = ?
            ORDER BY 
                CASE 
                    WHEN current_stock <= minimum_stock THEN 1
                    WHEN current_stock <= reorder_point THEN 2
                    ELSE 3
                END,
                product_name
            LIMIT ?
        """, (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]


def get_inventory_summary(user_id: int) -> Dict[str, Any]:
    """Get inventory summary statistics using CORRECT logic."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total items
        cursor.execute("SELECT COUNT(*) as total FROM inventory WHERE user_id = ?", (user_id,))
        total_items = cursor.fetchone()['total']
        
        # CRITICAL: current_stock <= minimum_stock
        cursor.execute("""
            SELECT COUNT(*) as count FROM inventory 
            WHERE user_id = ? AND current_stock <= minimum_stock
        """, (user_id,))
        critical_stock = cursor.fetchone()['count']
        
        # LOW: current_stock <= reorder_point AND current_stock > minimum_stock
        cursor.execute("""
            SELECT COUNT(*) as count FROM inventory 
            WHERE user_id = ? AND current_stock <= reorder_point AND current_stock > minimum_stock
        """, (user_id,))
        low_stock = cursor.fetchone()['count']
        
        # Total inventory value
        cursor.execute("""
            SELECT SUM(current_stock * unit_price) as total_value 
            FROM inventory WHERE user_id = ? AND unit_price IS NOT NULL AND unit_price > 0
        """, (user_id,))
        total_value = cursor.fetchone()['total_value'] or 0
        
        return {
            'total_items': total_items,
            'low_stock': low_stock,
            'critical_stock': critical_stock,
            'total_value': round(total_value, 2)
        }


def get_raw_material_suggestions(user_id: int, forecast_days: int = 7) -> Dict[str, Any]:
    """Suggest raw material quantities based on forecasted demand."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get average forecasted demand
        cursor.execute("""
            SELECT AVG(predicted_demand) as avg_daily_demand
            FROM forecasts 
            WHERE user_id = ? 
            AND forecast_date >= DATE('now')
            AND forecast_date <= DATE('now', '+' || ? || ' days')
        """, (user_id, forecast_days))
        
        row = cursor.fetchone()
        avg_daily_demand = row['avg_daily_demand'] if row and row['avg_daily_demand'] else 100
        
        # Get all inventory items
        cursor.execute("""
            SELECT 
                id, product_name, category, unit, unit_price,
                current_stock, reorder_point, minimum_stock
            FROM inventory 
            WHERE user_id = ?
        """, (user_id,))
        
        inventory_items = [dict(row) for row in cursor.fetchall()]
        
        suggestions = []
        for item in inventory_items:
            # Calculate suggested order (7 days of demand - current stock)
            suggested_order = max(0, (avg_daily_demand * 7) - item['current_stock'])
            
            # Determine correct status using your logic
            if item['current_stock'] <= item['minimum_stock']:
                status = 'critical'
            elif item['current_stock'] <= item['reorder_point']:
                status = 'low'
            else:
                status = 'normal'
            
            suggestions.append({
                'id': item['id'],
                'product_name': item['product_name'],
                'category': item['category'],
                'unit': item['unit'],
                'current_stock': item['current_stock'],
                'reorder_point': item['reorder_point'],
                'minimum_stock': item['minimum_stock'],
                'suggested_order': round(suggested_order, 1),
                'status': status,
                'trend': 'stable'  # You can calculate trend if you have historical data
            })
        
        # Sort by status: critical first, then low, then normal
        status_order = {'critical': 0, 'low': 1, 'normal': 2}
        suggestions.sort(key=lambda x: status_order.get(x['status'], 3))
        
        return {
            'avg_daily_demand': round(avg_daily_demand, 0),
            'total_weekly_demand': round(avg_daily_demand * 7, 0),
            'suggestions': suggestions
        }


def get_inventory_alerts(user_id: int) -> List[Dict[str, Any]]:
    """Get inventory-related alerts based on CORRECT logic."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        alerts = []
        
        # CRITICAL alerts (below minimum stock)
        cursor.execute("""
            SELECT product_name, current_stock, minimum_stock, unit
            FROM inventory 
            WHERE user_id = ? AND current_stock <= minimum_stock
            ORDER BY current_stock ASC
            LIMIT 5
        """, (user_id,))
        
        critical_items = [dict(row) for row in cursor.fetchall()]
        
        for item in critical_items:
            alerts.append({
                'type': 'critical_inventory',
                'title': 'CRITICAL: ' + item['product_name'],
                'message': f"Only {item['current_stock']} {item['unit']} left! Minimum is {item['minimum_stock']} {item['unit']}. Order IMMEDIATELY!",
                'priority': 'critical',
                'icon': 'skull-crosswalk',
                'color': '#ef4444'
            })
        
        # LOW alerts (below reorder point but above minimum)
        cursor.execute("""
            SELECT product_name, current_stock, reorder_point, minimum_stock, unit
            FROM inventory 
            WHERE user_id = ? AND current_stock <= reorder_point AND current_stock > minimum_stock
            ORDER BY current_stock ASC
            LIMIT 5
        """, (user_id,))
        
        low_items = [dict(row) for row in cursor.fetchall()]
        
        for item in low_items:
            alerts.append({
                'type': 'low_inventory',
                'title': 'Low Stock: ' + item['product_name'],
                'message': f"{item['current_stock']} {item['unit']} remaining. Reorder at {item['reorder_point']} {item['unit']}.",
                'priority': 'high',
                'icon': 'exclamation-triangle',
                'color': '#f59e0b'
            })
        
        return alerts

def add_inventory_item(user_id: int, item_data: Dict[str, Any]) -> int:
    """Add a new inventory item."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO inventory (
                user_id, product_name, category, unit, unit_price,
                current_stock, reorder_point, minimum_stock, supplier,
                storage_location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            item_data.get('product_name'),
            item_data.get('category'),
            item_data.get('unit'),
            item_data.get('unit_price'),
            item_data.get('current_stock', 0),
            item_data.get('reorder_point', 50),
            item_data.get('minimum_stock', 20),
            item_data.get('supplier'),
            item_data.get('storage_location')
        ))
        
        return cursor.lastrowid