"""
Helper functions for Food Forecast AI.
Includes password hashing (Werkzeug), CSRF protection, validation, and decorators.
"""

import os
import uuid
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, flash, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================
# PASSWORD HASHING (Werkzeug PBKDF2)
# ============================================

def hash_password(password: str) -> str:
    """
    Hash a password using Werkzeug's PBKDF2 with SHA256.
    This is the industry standard for Flask web applications.
    
    Args:
        password: Plain text password
        
    Returns:
        Secure password hash string
    """
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


# ============================================
# CSRF PROTECTION
# ============================================

def generate_csrf_token() -> str:
    """
    Generate a new CSRF token and store in session.
    
    Returns:
        CSRF token string
    """
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token(token: str) -> bool:
    """
    Validate a CSRF token against the one stored in session.
    
    Args:
        token: Token to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not token:
        return False
    session_token = session.get('csrf_token')
    if not session_token:
        return False
    return secrets.compare_digest(session_token, token)


def csrf_token() -> str:
    """Template-friendly CSRF token getter."""
    return generate_csrf_token()


# ============================================
# SESSION & AUTHENTICATION
# ============================================

def set_user_session(user: dict, remember: bool = False) -> None:
    """
    Set user session variables after successful login/signup.
    
    Args:
        user: User dictionary from database
        remember: If True, session lasts longer (30 days)
    """
    session['user_id'] = user['id']
    session['user_email'] = user['email']
    session['user_name'] = f"{user['first_name']} {user['last_name']}"
    session['user_first_name'] = user['first_name']
    session['user_last_name'] = user['last_name']
    session['user_role'] = user.get('role', 'user')
    session['restaurant_name'] = user.get('restaurant_name', '')
    session['plan'] = user.get('plan', 'professional')
    session['theme'] = user.get('theme_preference', 'light')
    
    # Generate new CSRF token for the session
    session['csrf_token'] = secrets.token_hex(32)
    
    # Set session expiry
    if remember:
        session.permanent = True
    else:
        session.permanent = False


def clear_user_session() -> None:
    """Clear all user-related session variables."""
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_first_name', None)
    session.pop('user_last_name', None)
    session.pop('user_role', None)
    session.pop('restaurant_name', None)
    session.pop('plan', None)
    session.pop('theme', None)
    session.pop('csrf_token', None)


def is_authenticated() -> bool:
    """Check if user is currently authenticated."""
    return 'user_id' in session


def get_current_user() -> dict:
    """
    Get current user info from session.
    Returns dict with user data or None if not authenticated.
    """
    if not is_authenticated():
        return None
    
    return {
        'id': session.get('user_id'),
        'email': session.get('user_email'),
        'name': session.get('user_name'),
        'first_name': session.get('user_first_name'),
        'last_name': session.get('user_last_name'),
        'role': session.get('user_role'),
        'restaurant_name': session.get('restaurant_name'),
        'plan': session.get('plan'),
        'theme': session.get('theme', 'light')
    }


def login_required(f):
    """
    Decorator to require authentication for routes.
    
    Usage:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return render_template('dashboard.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# FLASH MESSAGES (Type-safe)
# ============================================

def flash_success(message: str) -> None:
    """Flash a success message."""
    flash(message, 'success')


def flash_error(message: str) -> None:
    """Flash an error message."""
    flash(message, 'error')


def flash_warning(message: str) -> None:
    """Flash a warning message."""
    flash(message, 'warning')


def flash_info(message: str) -> None:
    """Flash an info message."""
    flash(message, 'info')


# ============================================
# FILE UPLOAD HELPERS
# ============================================

def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename: Name of the uploaded file
        allowed_extensions: Set of allowed extensions (defaults to common data files)
        
    Returns:
        True if allowed, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = {'csv', 'xlsx', 'xls', 'json', 'pkl', 'txt'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def secure_filename_custom(filename: str) -> str:
    """
    Secure a filename using werkzeug's secure_filename and add UUID prefix.
    
    Args:
        filename: Original filename
        
    Returns:
        Secure filename with UUID prefix
    """
    # First secure the original filename
    base_filename = secure_filename(filename)
    
    # If secure_filename returns empty, generate a default name
    if not base_filename:
        base_filename = 'file'
    
    # Add UUID prefix to avoid collisions
    unique_id = str(uuid.uuid4())[:8]
    return f"{unique_id}_{base_filename}"


def save_uploaded_file(file, user_id: int, upload_folder: str = None) -> tuple:
    """
    Save an uploaded file to the user's upload directory.
    
    Args:
        file: File object from request.files
        user_id: ID of the user uploading
        upload_folder: Base upload folder (defaults to 'uploads')
        
    Returns:
        Tuple of (success: bool, error_message: str, file_data: dict)
    """
    if upload_folder is None:
        upload_folder = 'uploads'
    
    if not file or file.filename == '':
        return False, 'No file selected', None
    
    if not allowed_file(file.filename):
        return False, f'File type not allowed. Allowed: csv, xlsx, xls, json, pkl, txt', None
    
    try:
        # Create user-specific upload directory
        user_upload_dir = os.path.join(upload_folder, str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Create secure filename
        original_filename = file.filename
        secure_name = secure_filename_custom(original_filename)
        file_path = os.path.join(user_upload_dir, secure_name)
        
        # Save file
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Determine file type
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
        
        file_data = {
            'filename': secure_name,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': file_ext,
            'description': ''
        }
        
        return True, None, file_data
        
    except Exception as e:
        return False, f'Error saving file: {str(e)}', None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., '2.5 MB')
    """
    if size_bytes == 0:
        return '0 Bytes'
    
    size_names = ['Bytes', 'KB', 'MB', 'GB']
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


# ============================================
# VALIDATION HELPERS
# ============================================

def validate_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_password_strength(password: str) -> tuple:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid: bool, message: str, score: int)
        Score is 0-4 (weak to very strong)
    """
    if not password:
        return False, 'Password is required', 0
    
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long', 1
    
    score = 0
    messages = []
    
    # Check for uppercase
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        messages.append('uppercase letter')
    
    # Check for lowercase
    if re.search(r'[a-z]', password):
        score += 1
    else:
        messages.append('lowercase letter')
    
    # Check for digit
    if re.search(r'\d', password):
        score += 1
    else:
        messages.append('number')
    
    # Check for special character
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        messages.append('special character')
    
    if score >= 3:
        return True, f'Password is strong (needs: {", ".join(messages)})' if messages else 'Password is strong', score
    elif score == 2:
        return True, f'Password is medium (add: {", ".join(messages)})', score
    else:
        return False, f'Password is weak. Add: {", ".join(messages)}', score


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format (basic).
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid format, False otherwise
    """
    # Remove common separators and spaces
    clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it's a valid phone number (8-15 digits)
    return re.match(r'^\d{8,15}$', clean_phone) is not None


# ============================================
# PAGINATION HELPERS
# ============================================

def get_pagination_info(current_page: int, total_items: int, items_per_page: int = 10, max_page_links: int = 5) -> dict:
    """
    Generate pagination information for templates.
    
    Args:
        current_page: Current page number (1-indexed)
        total_items: Total number of items
        items_per_page: Number of items per page
        max_page_links: Maximum number of page links to show
        
    Returns:
        Dictionary with pagination data
    """
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Ensure current page is within bounds
    current_page = max(1, min(current_page, total_pages)) if total_pages > 0 else 1
    
    # Calculate start and end indices for page links
    half_links = max_page_links // 2
    start_page = max(1, current_page - half_links)
    end_page = min(total_pages, start_page + max_page_links - 1)
    
    # Adjust start_page if end_page is at max
    if end_page - start_page + 1 < max_page_links and start_page > 1:
        start_page = max(1, end_page - max_page_links + 1)
    
    page_range = list(range(start_page, end_page + 1))
    
    return {
        'current_page': current_page,
        'total_pages': total_pages,
        'pages': total_pages,
        'total_items': total_items,
        'items_per_page': items_per_page,
        'has_prev': current_page > 1,
        'has_next': current_page < total_pages,
        'prev_page': current_page - 1 if current_page > 1 else 1,
        'next_page': current_page + 1 if current_page < total_pages else total_pages,
        'page_range': page_range,
        'start_index': (current_page - 1) * items_per_page + 1 if total_items > 0 else 0,
        'end_index': min(current_page * items_per_page, total_items)
    }


# ============================================
# MODEL CONFIGURATION HELPERS
# ============================================

def get_available_models() -> dict:
    """
    Get available ML models configuration.
    This imports from config to avoid circular imports.
    """
    try:
        from config import Config
        return Config.AVAILABLE_MODELS
    except ImportError:
        # Fallback if config not available
        return {}


def get_model_by_key(model_key: str) -> dict:
    """
    Get model configuration by key.
    
    Args:
        model_key: Model identifier (linear, arima, lstm, xgboost, gru)
        
    Returns:
        Model config dict or None if not found
    """
    models = get_available_models()
    return models.get(model_key)


# ============================================
# UTILITY FUNCTIONS
# ============================================

def generate_unique_id() -> str:
    """Generate a unique ID string."""
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def sanitize_input(text: str) -> str:
    """
    Basic input sanitization.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ''
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any script-like content
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    return text.strip()