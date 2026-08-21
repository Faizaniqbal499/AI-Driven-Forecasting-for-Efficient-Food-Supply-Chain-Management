"""
Food Forecast AI - Main Flask Application
"""

import os
import sys
import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

_current_forecast_data = {}

from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, send_file
)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config import get_config, Config

# Import helpers
from utils.helpers import (
    hash_password, verify_password, login_required, 
    allowed_file, save_uploaded_file, format_file_size,
    generate_csrf_token, validate_csrf_token, csrf_token,
    validate_email, validate_password_strength, validate_phone,
    set_user_session, clear_user_session, is_authenticated, get_current_user,
    flash_success, flash_error, flash_warning, flash_info,
    get_pagination_info, get_available_models, get_model_by_key
)

# Import database functions
from database.db import (
    get_db, init_db, create_user, get_user_by_email, get_user_by_id,
    update_last_login, update_theme_preference,
    save_uploaded_file as db_save_file, get_user_files, get_file_by_id,
    delete_file, update_file_status,
    get_dashboard_stats, get_folder_stats, get_top_menu_items,
    get_alerts, get_forecast_data, get_age_distribution,
    save_forecast, get_recent_models, create_model_run, update_model_run,
    log_audit, create_session, invalidate_session,
    get_inventory_items, get_inventory_summary, 
    get_raw_material_suggestions, get_inventory_alerts, add_inventory_item
)

# ============================================
# IMPORT ACTUAL MODEL LOADER
# ============================================
try:
    from models.model_loader import load_model, predict, get_model_metadata
    MODELS_AVAILABLE = True
    print("✅ ML Model Loader imported successfully!")
except ImportError as e:
    print(f"⚠️ Warning: Could not import model_loader: {e}")
    print("   Running in demo mode with simulated forecasts.")
    MODELS_AVAILABLE = False

# ============================================
# FLASK APP INITIALIZATION
# ============================================

app = Flask(__name__)
app.config.from_object(get_config())

# Ensure a strong secret key is set
if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
    app.config['SECRET_KEY'] = os.urandom(24).hex()
    print("⚠️ Using generated secret key - please set a permanent one in config.py")

# Session Configuration (overrides config.py for inactivity timeout)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=50)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize database
with app.app_context():
    init_db()
    print("✅ Database initialized successfully!")


# ============================================
# SESSION MANAGEMENT - Before Request
# ============================================

@app.before_request
def make_session_permanent():
    """Make session permanent and reset timer on activity"""
    # Skip for static files and public routes
    if request.endpoint in ['static', 'login', 'signup', 'forgot_password', 
                            'google_login', 'microsoft_login', 'session_timeout', 'keep_alive']:
        return
    
    # If user is logged in, make session permanent
    if is_authenticated():
        session.permanent = True
        session.modified = True


# ============================================
# SESSION MANAGEMENT ROUTES
# ============================================

@app.route('/session-timeout', methods=['POST'])
def session_timeout():
    """Handle session timeout from frontend (inactivity or tab close)"""
    if 'user_id' in session:
        user_id = session.get('user_id')
        if user_id:
            log_audit(user_id, 'session_timeout', 'user', user_id, 'Session expired due to inactivity')
        clear_user_session()
    session.clear()
    return jsonify({'success': True})


@app.route('/keep-alive', methods=['POST'])
@login_required
def keep_alive():
    """Reset session timer - called by frontend on user activity"""
    session.permanent = True
    session.modified = True
    return jsonify({'success': True})


# ============================================
# CONTEXT PROCESSORS (Available in all templates)
# ============================================

@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'csrf_token': csrf_token,
        'user': get_current_user() if is_authenticated() else None,
        'is_authenticated': is_authenticated(),
        'app_name': Config.APP_NAME,
        'app_version': Config.APP_VERSION,
        'current_year': datetime.now().year
    }


@app.context_processor
def inject_csrf():
    """Inject CSRF token function into templates."""
    return {'csrf_token': csrf_token}


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    from database.db import get_db
    db = get_db()
    db.rollback() if hasattr(db, 'rollback') else None
    return render_template('500.html'), 500


# ============================================
# PUBLIC ROUTES (No Login Required)
# ============================================

@app.route('/')
def index():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not validate_csrf_token(token):
            flash_error('Invalid form submission. Please try again.')
            return redirect(url_for('signup'))
        
        form_data = {
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'phone': request.form.get('phone', '').strip(),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', ''),
            'restaurant_name': request.form.get('restaurant_name', '').strip(),
            'restaurant_type': request.form.get('restaurant_type', ''),
            'cuisine_type': request.form.get('cuisine_type', '').strip(),
            'location': request.form.get('location', '').strip(),
            'daily_customers': request.form.get('daily_customers', ''),
            'seating_capacity': request.form.get('seating_capacity', ''),
            'plan': request.form.get('plan', 'professional'),
            'terms': request.form.get('terms') == 'on'
        }
        
        errors = {}
        
        if not form_data['first_name']: errors['first_name'] = 'First name is required'
        if not form_data['last_name']: errors['last_name'] = 'Last name is required'
        if not validate_email(form_data['email']): errors['email'] = 'Please enter a valid email address'
        if form_data['phone'] and not validate_phone(form_data['phone']): errors['phone'] = 'Please enter a valid phone number'
        
        is_valid_pw, pw_message, pw_score = validate_password_strength(form_data['password'])
        if not is_valid_pw: errors['password'] = pw_message
        if form_data['password'] != form_data['confirm_password']: errors['confirm_password'] = 'Passwords do not match'
        
        if not form_data['restaurant_name']: errors['restaurant_name'] = 'Restaurant name is required'
        if not form_data['restaurant_type']: errors['restaurant_type'] = 'Please select restaurant type'
        if not form_data['location']: errors['location'] = 'Location is required'
        if not form_data['terms']: errors['terms'] = 'You must agree to the Terms of Service'
        
        existing_user = get_user_by_email(form_data['email'])
        if existing_user: errors['email'] = 'This email is already registered'
        
        if errors:
            return render_template('signup.html', errors=errors, form_data=form_data)
        
        try:
            password_hash = hash_password(form_data['password'])
            user_data = {
                'first_name': form_data['first_name'],
                'last_name': form_data['last_name'],
                'email': form_data['email'],
                'phone': form_data['phone'],
                'password_hash': password_hash,
                'restaurant_name': form_data['restaurant_name'],
                'restaurant_type': form_data['restaurant_type'],
                'cuisine_type': form_data['cuisine_type'],
                'location': form_data['location'],
                'daily_customers': int(form_data['daily_customers']) if form_data['daily_customers'] else None,
                'seating_capacity': int(form_data['seating_capacity']) if form_data['seating_capacity'] else None,
                'plan': form_data['plan']
            }
            
            user_id = create_user(user_data)
            log_audit(user_id, 'signup', 'user', user_id, f"New user registered: {form_data['email']}", request.remote_addr, request.user_agent.string)
            flash_success('Account created successfully! Welcome to Food Forecast AI.')
            
            user = get_user_by_id(user_id)
            set_user_session(user)
            update_last_login(user_id)
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            app.logger.error(f"Signup error: {str(e)}")
            flash_error('An error occurred during registration. Please try again.')
            return render_template('signup.html', form_data=form_data)
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    next_url = request.args.get('next', url_for('dashboard'))
    
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not validate_csrf_token(token):
            flash_error('Invalid form submission. Please try again.')
            return redirect(url_for('login'))
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        # Check for both 'true' (string) and 'on' (checkbox) values
        remember = request.form.get('remember') in ['true', 'on', True]
        
        errors = {}
        if not email: errors['email'] = 'Email is required'
        if not password: errors['password'] = 'Password is required'
        
        if errors:
            return render_template('login.html', errors=errors, form_data={'email': email})
        
        user = get_user_by_email(email)
        
        if not user:
            errors['email'] = 'No account found with this email'
        elif not verify_password(password, user['password_hash']):
            errors['password'] = 'Incorrect password'
        elif not user.get('is_active', True):
            errors['email'] = 'This account has been deactivated'
        
        if errors:
            return render_template('login.html', errors=errors, form_data={'email': email})
        
        # Set session with remember me
        set_user_session(user, remember=remember)
        
        # Make session permanent if remember me is checked
        if remember:
            session.permanent = True
        
        update_last_login(user['id'])
        
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + (timedelta(days=30) if remember else timedelta(days=7))
        create_session(user['id'], session_token, expires_at, request.remote_addr, request.user_agent.string)
        
        log_audit(user['id'], 'login', 'user', user['id'], f"User logged in", request.remote_addr, request.user_agent.string)
        flash_success(f'Welcome back, {user["first_name"]}!')
        
        return redirect(next_url)
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    if is_authenticated():
        user_id = session.get('user_id')
        if user_id:
            log_audit(user_id, 'logout', 'user', user_id, 'User logged out')
        
        session_token = session.get('session_token')
        if session_token:
            invalidate_session(session_token)
        
        # Clear session and cookie
        clear_user_session()
        session.clear()
        
        # Clear the session cookie
        response = redirect(url_for('login'))
        response.set_cookie('session', '', expires=0)
        response.set_cookie('_session', '', expires=0)
        
        flash_info('You have been logged out.')
        return response
    
    session.clear()
    response = redirect(url_for('login'))
    response.set_cookie('session', '', expires=0)
    return response


@app.route('/forgot-password')
def forgot_password():
    flash_info('Password reset functionality will be implemented soon.')
    return redirect(url_for('login'))


@app.route('/set-theme', methods=['POST'])
@login_required
def set_theme():
    try:
        data = request.get_json()
        theme = data.get('theme', 'light')
        user_id = session['user_id']
        update_theme_preference(user_id, theme)
        session['theme'] = theme
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/google-login')
def google_login():
    flash_info('Google login will be available soon.')
    return redirect(url_for('login'))


@app.route('/microsoft-login')
def microsoft_login():
    flash_info('Microsoft login will be available soon.')
    return redirect(url_for('login'))


# ============================================
# DASHBOARD ROUTES
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = get_current_user()
    
    stats = get_dashboard_stats(user_id)
    top_items = get_top_menu_items(user_id, limit=4)
    alerts = get_alerts(user_id, limit=5)
    forecast_data = get_forecast_data(user_id, days=7)
    age_distribution = get_age_distribution(user_id)

    # Store the current forecast data in session for report downloads
    session['current_forecast_data'] = forecast_data
    
    # Also store in global for backup
    global _current_forecast_data
    _current_forecast_data = {
        'data': forecast_data,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }

    # DEBUG: Print what was retrieved
    print(f"DEBUG DASHBOARD: Retrieved {len(forecast_data)} forecast items")
    for fd in forecast_data:
        print(f"  - {fd}")
    
    return render_template('dashboard.html',
                          user=user,
                          stats=stats,
                          top_items=top_items,
                          alerts=alerts,
                          forecast_data=forecast_data,
                          age_distribution=age_distribution)


@app.route('/dashboard-data')
@login_required
def dashboard_data():
    user_id = session['user_id']
    period = request.args.get('period', 'today')
    stats = get_dashboard_stats(user_id)
    return jsonify({'success': True, 'stats': stats, 'period': period})


@app.route('/switch-restaurant', methods=['POST'])
@login_required
def switch_restaurant():
    data = request.get_json()
    restaurant = data.get('restaurant', '')
    session['current_restaurant'] = restaurant
    return jsonify({'success': True})


# ============================================
# DATA MANAGEMENT ROUTES
# ============================================

@app.route('/data-management')
@login_required
def data_management():
    user_id = session['user_id']
    user = get_current_user()
    
    page = request.args.get('page', 1, type=int)
    folder = request.args.get('folder')
    search = request.args.get('search')
    view = request.args.get('view', 'files')
    
    per_page = app.config['ITEMS_PER_PAGE']
    offset = (page - 1) * per_page
    
    files, total_files = get_user_files(user_id, folder=folder, search=search, limit=per_page, offset=offset)
    pagination = get_pagination_info(page, total_files, per_page)
    
    folders = get_folder_stats(user_id)
    stats = get_dashboard_stats(user_id)

    # Enhance files with display name
    for file in files:
        if '_' in file['original_filename']:
            parts = file['original_filename'].split('_', 1)
            if len(parts) == 2 and len(parts[0]) == 32:
                file['display_name'] = parts[1]
            else:
                file['display_name'] = file['original_filename']
        else:
            file['display_name'] = file['original_filename']
    
    return render_template('data_management.html',
                          user=user,
                          files=files,
                          folders=folders,
                          stats=stats,
                          pagination=pagination,
                          search_query=search,
                          view=view)


@app.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    user_id = session['user_id']
    
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    if not validate_csrf_token(token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': f'File type not allowed. Allowed: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'})
    
    success, error, file_data = save_uploaded_file(file, user_id)
    if not success:
        return jsonify({'success': False, 'error': error})
    
    try:
        file_id = db_save_file(user_id, file_data)
        log_audit(user_id, 'upload', 'file', file_id, f"Uploaded: {file_data['original_filename']}", request.remote_addr, request.user_agent.string)
        return jsonify({'success': True, 'file_id': file_id, 'filename': file_data['original_filename']})
    except Exception as e:
        app.logger.error(f"Database error during upload: {str(e)}")
        return jsonify({'success': False, 'error': 'Database error'})


@app.route('/preview-file/<int:file_id>')
@login_required
def preview_file(file_id):
    user_id = session['user_id']
    file_info = get_file_by_id(file_id, user_id)
    if not file_info:
        flash_error('File not found')
        return redirect(url_for('data_management'))
    flash_info(f'Preview for {file_info["original_filename"]}')
    return redirect(url_for('data_management'))


@app.route('/download-file/<int:file_id>')
@login_required
def download_file(file_id):
    user_id = session['user_id']
    file_info = get_file_by_id(file_id, user_id)
    if not file_info:
        flash_error('File not found')
        return redirect(url_for('data_management'))
    
    file_path = file_info['file_path']
    if not os.path.exists(file_path):
        flash_error('File not found on server')
        return redirect(url_for('data_management'))
    
    log_audit(user_id, 'download', 'file', file_id, f"Downloaded: {file_info['original_filename']}")
    return send_file(file_path, download_name=file_info['original_filename'], as_attachment=True)


@app.route('/process-file/<int:file_id>', methods=['POST'])
@login_required
def process_file(file_id):
    user_id = session['user_id']
    file_info = get_file_by_id(file_id, user_id)
    if not file_info:
        return jsonify({'success': False, 'error': 'File not found'})
    
    update_file_status(file_id, 'processing')
    log_audit(user_id, 'process', 'file', file_id, f"Started processing: {file_info['original_filename']}")
    return jsonify({'success': True, 'redirect': url_for('ml_models', file_id=file_id)})


@app.route('/delete-file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file_route(file_id):
    user_id = session['user_id']
    success = delete_file(file_id, user_id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404


@app.route('/bulk-process', methods=['POST'])
@login_required
def bulk_process():
    user_id = session['user_id']
    data = request.get_json()
    file_ids = data.get('file_ids', [])
    if not file_ids:
        return jsonify({'success': False, 'error': 'No files selected'})
    
    for file_id in file_ids:
        update_file_status(file_id, 'processing')
    log_audit(user_id, 'bulk_process', 'files', 0, f"Bulk processed {len(file_ids)} files")
    return jsonify({'success': True, 'redirect': url_for('ml_models', files=','.join(map(str, file_ids)))})


@app.route('/bulk-download')
@login_required
def bulk_download():
    flash_info('Bulk download will be available soon.')
    return redirect(url_for('data_management'))


@app.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    user_id = session['user_id']
    data = request.get_json()
    file_ids = data.get('file_ids', [])
    if not file_ids:
        return jsonify({'success': False, 'error': 'No files selected'})
    
    deleted = 0
    for file_id in file_ids:
        if delete_file(file_id, user_id):
            deleted += 1
    log_audit(user_id, 'bulk_delete', 'files', 0, f"Deleted {deleted} files")
    return jsonify({'success': True, 'deleted': deleted})


# ============================================
# ML MODELS ROUTES
# ============================================

@app.route('/ml-models')
@login_required
def ml_models():
    user_id = session['user_id']
    user = get_current_user()
    
    # Get models from config
    models = list(get_available_models().values())
    
    # Enhance with metadata from actual model loader if available
    if MODELS_AVAILABLE:
        try:
            for model in models:
                metadata = get_model_metadata(model['key'])
                if metadata:
                    model['accuracy'] = f"{metadata.get('accuracy', 0) * 100:.0f}%"
                    model['size'] = metadata.get('size', 'Unknown')
        except Exception as e:
            app.logger.warning(f"Could not load model metadata: {e}")
    
    recent_models = get_recent_models(user_id, limit=4)
    
    # Get ALL files for the user - no status filtering
    # Remove the status filtering to show all files
    all_files, _ = get_user_files(user_id, limit=100)  # Get all files without status filter
    
    # Also get files that are ready for processing (for visual indication)
    pending_files, _ = get_user_files(user_id, status='pending', limit=100)
    processing_files, _ = get_user_files(user_id, status='processing', limit=100)
    
    # Combine: show all files, but mark which ones are ready for processing
    files = []
    file_ids_in_processing = {f['id'] for f in pending_files + processing_files}
    
    for file in all_files:
        # Add a flag indicating if this file can be processed
        file['can_process'] = file['id'] in file_ids_in_processing or file['status'] in ['pending', 'processing']
        files.append(file)
    
    file_id = request.args.get('file_id', type=int)
    
    # If file_id is provided but file is not in the list, add it
    if file_id and not any(f['id'] == file_id for f in files):
        single_file = get_file_by_id(file_id, user_id)
        if single_file:
            single_file['can_process'] = True
            files.insert(0, single_file)

    # Add display names for all files
    for file in files:
        if '_' in file['original_filename']:
            parts = file['original_filename'].split('_', 1)
            if len(parts) == 2 and len(parts[0]) == 32:
                file['display_name'] = parts[1]
            else:
                file['display_name'] = file['original_filename']
        else:
            file['display_name'] = file['original_filename']
    
    return render_template('ml_models.html',
                          user=user,
                          models=models,
                          recent_models=recent_models,
                          available_files=files,
                          selected_file_id=file_id)

@app.route('/run-forecast', methods=['POST'])
@login_required
def run_forecast():
    user_id = session['user_id']
    
    token = request.headers.get('X-CSRFToken')
    if not validate_csrf_token(token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'})
    
    data = request.get_json()
    model_key = data.get('model')
    file_id = data.get('file_id')
    
    if not model_key or not file_id:
        return jsonify({'success': False, 'error': 'Missing model or file selection'})
    
    model = get_model_by_key(model_key)
    if not model or not model.get('enabled', False):
        return jsonify({'success': False, 'error': 'Invalid model selected'})
    
    file_info = get_file_by_id(file_id, user_id)
    if not file_info:
        return jsonify({'success': False, 'error': 'File not found'})
    
    # Create model run record
    run_id = create_model_run(user_id, model_key, file_id)
    update_file_status(file_id, 'processing')
    
    log_audit(user_id, 'forecast', 'model_run', run_id, f"Started {model['name']} forecast on {file_info['original_filename']}")
    
    try:
        # ============================================
        # USE ACTUAL TRAINED MODEL (Not Simulation)
        # ============================================
        if MODELS_AVAILABLE:
            # Load data from uploaded file
            file_path = file_info['file_path']
            if file_path.endswith('.csv'):
                input_data = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                input_data = pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                input_data = pd.read_json(file_path)
            else:
                raise ValueError("Unsupported file format for forecasting")
            
            # Load the pre-trained model
            loaded_model = load_model(model_key)
            
            # Generate predictions
            predictions = predict(loaded_model, input_data, model_key)
            
            # Format results
            forecast_results = format_predictions_for_db(predictions, model_key, model)
        else:
            # Fallback to simulation if models not available
            forecast_results = simulate_forecast(user_id, model_key, file_id, model)
        
        # Save forecasts to database
        for fc in forecast_results:
            fc['model_name'] = model_key
            fc['input_file_id'] = file_id
            save_forecast(user_id, fc)

        # After saving forecasts, add this debug code
        print(f"DEBUG: Saved {len(forecast_results)} forecasts to database")
        for fc in forecast_results[:3]:  # Print first 3
            print(f"  - Date: {fc['forecast_date']}, Demand: {fc['predicted_demand']}")
        
        # Update model run as completed
        update_model_run(run_id, 'completed', {
            'forecast_count': len(forecast_results),
            'accuracy_achieved': float(model.get('accuracy', '90').replace('%', '')) / 100
        })
        
        update_file_status(file_id, 'processed')
        
        return jsonify({
            'success': True,
            'redirect': url_for('dashboard'),
            'message': f'Forecast completed using {model["name"]}'
        })
        
    except Exception as e:
        app.logger.error(f"Forecast error: {str(e)}")
        update_model_run(run_id, 'failed', {'error': str(e)})
        update_file_status(file_id, 'failed', str(e))
        return jsonify({'success': False, 'error': f'Forecast failed: {str(e)}'})


def format_predictions_for_db(predictions, model_key, model_config):
    """
    Format model predictions for database storage.
    """
    results = []
    today = datetime.now().date()
    
    if isinstance(predictions, (list, np.ndarray)):
        for i, pred in enumerate(predictions[:7]):  # Max 7 days
            # FIX: Use i+1 to get different dates (tomorrow, day after, etc.)
            forecast_date = today + timedelta(days=i+1)  # ← This is correct
            predicted_val = float(pred)
            margin = predicted_val * 0.05  # 5% confidence margin
            
            results.append({
                'forecast_date': forecast_date.isoformat(),
                'predicted_demand': int(predicted_val),
                'confidence_lower': int(predicted_val - margin),
                'confidence_upper': int(predicted_val + margin),
                'confidence_interval': 0.95,
                'accuracy_score': float(model_config.get('accuracy', '90').replace('%', '')) / 100,
                'target_type': 'overall'
            })
    else:
        # Single prediction
        forecast_date = today + timedelta(days=1)
        predicted_val = float(predictions)
        margin = predicted_val * 0.05
        
        results.append({
            'forecast_date': forecast_date.isoformat(),
            'predicted_demand': int(predicted_val),
            'confidence_lower': int(predicted_val - margin),
            'confidence_upper': int(predicted_val + margin),
            'confidence_interval': 0.95,
            'accuracy_score': float(model_config.get('accuracy', '90').replace('%', '')) / 100,
            'target_type': 'overall'
        })
    
    # Debug: Print the dates being generated
    for r in results:
        print(f"Generated forecast for: {r['forecast_date']} with demand {r['predicted_demand']}")
    
    return results


def simulate_forecast(user_id: int, model_key: str, file_id: int, model_config: dict) -> list:
    """
    Fallback simulation if model_loader is not available.
    """
    import random
    import numpy as np
    
    forecasts = []
    today = datetime.now().date()
    base_accuracy = float(model_config.get('accuracy', '90').replace('%', '')) / 100
    
    for i in range(1, 8):
        forecast_date = today + timedelta(days=i)
        base_demand = 150
        day_factor = 1.2 if forecast_date.weekday() >= 5 else 1.0
        predicted = int(base_demand * day_factor * random.uniform(0.9, 1.1))
        margin = int(predicted * (1 - base_accuracy))
        
        forecasts.append({
            'forecast_date': forecast_date.isoformat(),
            'predicted_demand': predicted,
            'confidence_lower': predicted - margin,
            'confidence_upper': predicted + margin,
            'confidence_interval': 0.95,
            'accuracy_score': base_accuracy,
            'target_type': 'overall'
        })
    
    return forecasts


# ============================================
# OTHER PAGES (Placeholders)
# ============================================

@app.route('/menu-items')
@login_required
def menu_items():
    flash_info('Menu items management will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/menu-item/<int:item_id>')
@login_required
def menu_item_detail(item_id):
    flash_info('Menu item details will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/customer-analytics')
@login_required
def customer_analytics():
    flash_info('Customer analytics will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/inventory')
@login_required
def inventory():
    user_id = session['user_id']
    user = get_current_user()
    
    # Get inventory data
    inventory_items = get_inventory_items(user_id)
    inventory_summary = get_inventory_summary(user_id)
    inventory_suggestions = get_raw_material_suggestions(user_id)
    inventory_alerts = get_inventory_alerts(user_id)
    
    return render_template('inventory.html',
                          user=user,
                          inventory_items=inventory_items,
                          inventory_summary=inventory_summary,
                          suggestions=inventory_suggestions,
                          alerts=inventory_alerts)

@app.route('/add-inventory-item', methods=['GET', 'POST'])
@login_required
def add_inventory_item():
    user_id = session['user_id']
    
    # Handle GET request (from our simple form)
    if request.method == 'GET':
        token = request.args.get('csrf_token')
        if not validate_csrf_token(token):
            flash_error('Invalid CSRF token')
            return redirect(url_for('inventory'))
        
        try:
            product_name = request.args.get('product_name', '').strip()
            if not product_name:
                flash_error('Product name is required')
                return redirect(url_for('inventory'))
            
            item_data = {
                'product_name': product_name,
                'category': request.args.get('category'),
                'unit': request.args.get('unit', 'kg'),
                'unit_price': float(request.args.get('unit_price')) if request.args.get('unit_price') else None,
                'current_stock': float(request.args.get('current_stock', 0)),
                'reorder_point': float(request.args.get('reorder_point', 50)),
                'minimum_stock': float(request.args.get('minimum_stock', 20)),
                'supplier': request.args.get('supplier'),
                'storage_location': request.args.get('storage_location', 'shelf')
            }
            
            from database.db import add_inventory_item as db_add_item
            item_id = db_add_item(user_id, item_data)
            
            if item_id:
                flash_success(f'Added inventory item: {product_name}')
                log_audit(user_id, 'add', 'inventory', item_id, f"Added inventory item: {product_name}")
            else:
                flash_error('Could not add inventory item')
                
        except Exception as e:
            flash_error(f'Error: {str(e)}')
        
        return redirect(url_for('inventory'))
    
    # Handle POST request (for API compatibility)
    elif request.method == 'POST':
        token = request.form.get('csrf_token')
        if not validate_csrf_token(token):
            return jsonify({'success': False, 'error': 'Invalid CSRF token'})
        
        try:
            product_name = request.form.get('product_name', '').strip()
            if not product_name:
                return jsonify({'success': False, 'error': 'Product name is required'})
            
            from database.db import add_inventory_item as db_add_item
            
            item_data = {
                'product_name': product_name,
                'category': request.form.get('category'),
                'unit': request.form.get('unit', 'kg'),
                'unit_price': float(request.form.get('unit_price')) if request.form.get('unit_price') else None,
                'current_stock': float(request.form.get('current_stock', 0)),
                'reorder_point': float(request.form.get('reorder_point', 50)),
                'minimum_stock': float(request.form.get('minimum_stock', 20)),
                'supplier': request.form.get('supplier'),
                'storage_location': request.form.get('storage_location', 'shelf')
            }
            
            item_id = db_add_item(user_id, item_data)
            
            if item_id:
                log_audit(user_id, 'add', 'inventory', item_id, f"Added inventory item: {product_name}")
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Database error'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/get-inventory-item/<int:item_id>')
@login_required
def get_inventory_item(item_id):
    """Get single inventory item for editing."""
    user_id = session['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, product_name, category, unit, unit_price,
                   current_stock, reorder_point, minimum_stock,
                   supplier, storage_location
            FROM inventory 
            WHERE id = ? AND user_id = ?
        """, (item_id, user_id))
        
        row = cursor.fetchone()
        if row:
            return jsonify({'success': True, 'item': dict(row)})
        else:
            return jsonify({'success': False, 'error': 'Item not found'})


@app.route('/update-inventory-item', methods=['GET', 'POST'])
@login_required
def update_inventory_item():
    """Update an existing inventory item."""
    user_id = session['user_id']
    
    # Handle both GET and POST
    if request.method == 'GET':
        token = request.args.get('csrf_token')
        params = request.args
    else:
        token = request.form.get('csrf_token')
        params = request.form
    
    if not validate_csrf_token(token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'})
    
    try:
        item_id = params.get('item_id')
        product_name = params.get('product_name', '').strip()
        
        if not product_name:
            return jsonify({'success': False, 'error': 'Product name is required'})
        
        # Validate no negative values
        current_stock = float(params.get('current_stock', 0))
        unit_price = params.get('unit_price')
        unit_price = float(unit_price) if unit_price and unit_price.strip() else None
        reorder_point = float(params.get('reorder_point', 50))
        minimum_stock = float(params.get('minimum_stock', 20))
        
        if current_stock < 0:
            return jsonify({'success': False, 'error': 'Stock cannot be negative'})
        if unit_price and unit_price < 0:
            return jsonify({'success': False, 'error': 'Price cannot be negative'})
        if reorder_point < 0:
            return jsonify({'success': False, 'error': 'Reorder point cannot be negative'})
        if minimum_stock < 0:
            return jsonify({'success': False, 'error': 'Minimum stock cannot be negative'})
        
        # Use the same database connection as your main app
        from database.db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE inventory 
                SET product_name = ?, category = ?, unit = ?, 
                    current_stock = ?, unit_price = ?,
                    reorder_point = ?, minimum_stock = ?,
                    supplier = ?, storage_location = ?
                WHERE id = ? AND user_id = ?
            """, (
                product_name,
                params.get('category'),
                params.get('unit', 'kg'),
                current_stock,
                unit_price,
                reorder_point,
                minimum_stock,
                params.get('supplier'),
                params.get('storage_location', 'shelf'),
                item_id,
                user_id
            ))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                conn.close()
                return jsonify({'success': True, 'message': 'Item updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'Item not found or no changes made'})
                
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
                
    except Exception as e:
        print(f"Update error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/delete-inventory-item/<int:item_id>', methods=['DELETE', 'GET'])
@login_required
def delete_inventory_item(item_id):
    """Delete an inventory item."""
    user_id = session['user_id']
    
    if request.method == 'DELETE':
        token = request.args.get('csrf_token')
    else:
        token = request.args.get('csrf_token')
    
    if not validate_csrf_token(token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'})
    
    try:
        from database.db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get product name for logging
        cursor.execute("SELECT product_name FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Item not found'})
        
        product_name = row['product_name']
        
        # Delete the item
        cursor.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            conn.close()
            return jsonify({'success': True, 'message': f'Deleted {product_name}'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Could not delete item'})
                
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/waste-management')
@login_required
def waste_management():
    flash_info('Waste management features will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/reports')
@login_required
def reports():
    flash_info('Advanced reporting will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/settings')
@login_required
def settings():
    flash_info('Settings and preferences will be available in a future update.')
    return redirect(url_for('dashboard'))

@app.route('/alerts')
@login_required
def alerts():
    user_id = session['user_id']
    alerts = get_alerts(user_id, limit=50)
    return render_template('alerts.html', user=get_current_user(), alerts=alerts)

@app.route('/resolve-alert', methods=['POST'])
@login_required
def resolve_alert():
    user_id = session['user_id']
    data = request.get_json()
    alert_id = data.get('alert_id')
    log_audit(user_id, 'resolve', 'alert', alert_id, 'Alert resolved')
    return jsonify({'success': True})

# ============================================
# ITEM FORECAST API ROUTES (Feature a)
# ============================================

@app.route('/api/items')
@login_required
def api_get_items():
    """Get all menu items from meal_info.csv"""
    try:
        from item_forecast import get_all_menu_items
        
        items = get_all_menu_items()
        
        if not items:
            return jsonify({
                'status': 'error',
                'message': 'No menu items found. Please upload meal_info.csv'
            }), 404
        
        return jsonify({
            'status': 'success',
            'items': items,
            'total': len(items)
        })
        
    except Exception as e:
        app.logger.error(f"Error loading items: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/forecast/item/<int:meal_id>')
@login_required
def api_forecast_item_detail(meal_id):
    """Get forecast for a specific menu item"""
    try:
        user_id = session['user_id']
        days = request.args.get('days', default=7, type=int)
        use_cache = request.args.get('cache', default='true', type=str).lower() == 'true'
        
        if days < 1 or days > 30:
            return jsonify({
                'status': 'error',
                'message': 'Days must be between 1 and 30'
            }), 400
        
        from item_forecast import get_latest_uploaded_file, get_item_forecast, get_item_details
        
        file_path = get_latest_uploaded_file(user_id)
        
        if not file_path:
            return jsonify({
                'status': 'error',
                'message': 'No data file found. Please upload a data file first.'
            }), 404
        
        item_details = get_item_details(meal_id)
        
        if not item_details:
            return jsonify({
                'status': 'error',
                'message': f'Item {meal_id} not found in meal_info.csv'
            }), 404
        
        forecast_result = get_item_forecast(
            meal_id=meal_id,
            file_path=file_path,
            days_ahead=days,
            use_cache=use_cache
        )
        
        if forecast_result.get('status') == 'error':
            return jsonify({
                'status': 'error',
                'message': forecast_result.get('error', 'Unknown error generating forecast')
            }), 500
        
        # Store the selected item and forecast in session
        session['selected_item_id'] = meal_id
        session['selected_item_forecast'] = {
            'item': {
                'id': meal_id,
                'name': f"Item {meal_id}",
                'category': item_details.get('category', 'Unknown'),
                'cuisine': item_details.get('cuisine', 'Unknown')
            },
            'forecast': forecast_result
        }
        
        from database.db import log_audit
        log_audit(
            user_id,
            'item_forecast',
            'menu_item',
            meal_id,
            f"Generated {days}-day forecast for item {meal_id} (cache: {use_cache})"
        )
        
        return jsonify({
            'status': 'success',
            'item': {
                'id': meal_id,
                'name': f"Item {meal_id}",
                'category': item_details.get('category', 'Unknown'),
                'cuisine': item_details.get('cuisine', 'Unknown')
            },
            'forecast': forecast_result
        })
        
    except Exception as e:
        app.logger.error(f"Error generating item forecast: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/forecast/restore')
@login_required
def api_forecast_restore():
    """Restore the last selected item forecast from session"""
    try:
        selected_item_id = session.get('selected_item_id')
        selected_item_forecast = session.get('selected_item_forecast')
        
        if selected_item_id and selected_item_forecast:
            return jsonify({
                'status': 'success',
                'item_id': selected_item_id,
                'item': selected_item_forecast.get('item'),
                'forecast': selected_item_forecast.get('forecast')
            })
        else:
            return jsonify({
                'status': 'empty',
                'message': 'No stored forecast'
            })
            
    except Exception as e:
        app.logger.error(f"Error restoring forecast: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/forecast/download/<int:meal_id>')
@login_required
def api_download_forecast(meal_id):
    """Download forecast as PDF, Excel, or PNG"""
    try:
        user_id = session['user_id']
        format_type = request.args.get('format', default='pdf', type=str)
        
        if format_type not in ['pdf', 'excel', 'png']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format. Use pdf, excel, or png'
            }), 400
        
        from item_forecast import get_latest_uploaded_file, get_item_forecast, get_item_details
        from download_utils import download_forecast_pdf, download_forecast_excel, download_forecast_png
        
        file_path = get_latest_uploaded_file(user_id)
        
        if not file_path:
            return jsonify({
                'status': 'error',
                'message': 'No data file found'
            }), 404
        
        item_details = get_item_details(meal_id)
        
        if not item_details:
            return jsonify({
                'status': 'error',
                'message': f'Item {meal_id} not found'
            }), 404
        
        forecast_result = get_item_forecast(
            meal_id=meal_id,
            file_path=file_path,
            days_ahead=7
        )
        
        if forecast_result.get('status') == 'error':
            return jsonify({
                'status': 'error',
                'message': forecast_result.get('error', 'Error generating forecast')
            }), 500
        
        if format_type == 'pdf':
            buffer = download_forecast_pdf(forecast_result)
            filename = f"forecast_item_{meal_id}.pdf"
            mime_type = 'application/pdf'
        elif format_type == 'excel':
            buffer = download_forecast_excel(forecast_result)
            filename = f"forecast_item_{meal_id}.xlsx"
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            buffer = download_forecast_png(forecast_result)
            filename = f"forecast_item_{meal_id}.png"
            mime_type = 'image/png'
        
        from database.db import log_audit
        log_audit(
            user_id,
            'download_forecast',
            'menu_item',
            meal_id,
            f"Downloaded {format_type} forecast for item {meal_id}"
        )
        
        return send_file(
            buffer,
            download_name=filename,
            mimetype=mime_type,
            as_attachment=True
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading forecast: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================
# REPORT DOWNLOAD ROUTES (Feature b)
# ============================================

@app.route('/api/report/download', methods=['GET', 'POST'])
@login_required
def api_download_report():
    """Download the main forecast report as PDF or Excel"""
    try:
        user_id = session['user_id']
        format_type = request.args.get('format', default='pdf', type=str)
        
        if format_type not in ['pdf', 'excel']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format. Use pdf or excel'
            }), 400
        
        # Try to get data from POST request (from frontend)
        forecast_data = None
        if request.method == 'POST':
            data = request.get_json()
            if data and data.get('forecast_data'):
                forecast_data = data.get('forecast_data')
                print(f"REPORT: Using {len(forecast_data)} items from frontend POST")
        
        # If not from POST, try session
        if not forecast_data:
            forecast_data = session.get('current_forecast_data')
            print(f"REPORT: Using {len(forecast_data) if forecast_data else 0} items from session")
        
        # If not in session, try database
        if not forecast_data:
            from database.db import get_forecast_data
            forecast_data = get_forecast_data(user_id, days=7)
            print(f"REPORT: Using {len(forecast_data) if forecast_data else 0} items from database")
        
        if not forecast_data:
            return jsonify({
                'status': 'error',
                'message': 'No forecast data available. Please refresh the dashboard first.'
            }), 404
        
        # Get user info
        user = get_current_user()
        
        # Get stats for summary
        stats = get_dashboard_stats(user_id)
        
        # Generate report using the EXACT data
        from report_utils import generate_forecast_report_from_data
        
        # Log what we're using
        print(f"REPORT: Using {len(forecast_data)} forecast items")
        for fd in forecast_data[:3]:
            print(f"  - Date: {fd.get('forecast_date')}, Actual: {fd.get('actual')}, Predicted: {fd.get('predicted')}")
        
        if format_type == 'pdf':
            buffer = generate_forecast_report_from_data(forecast_data, user, stats, 'pdf')
            filename = f"forecast_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            mime_type = 'application/pdf'
        else:
            buffer = generate_forecast_report_from_data(forecast_data, user, stats, 'excel')
            filename = f"forecast_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        log_audit(
            user_id,
            'download_report',
            'report',
            0,
            f"Downloaded {format_type} forecast report"
        )
        
        # Check if buffer has content
        buffer.seek(0, 2)
        size = buffer.tell()
        buffer.seek(0)
        
        if size == 0:
            return jsonify({
                'status': 'error',
                'message': 'Generated report is empty'
            }), 500
        
        return send_file(
            buffer,
            download_name=filename,
            mimetype=mime_type,
            as_attachment=True
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading report: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MODELS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=app.config['DEBUG'])