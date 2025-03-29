from flask import Blueprint, request, redirect, url_for, session, jsonify
import secrets
import requests
from functools import wraps
from appwrite.id import ID
from app.utils.appwrite import get_database_service
from app.auth.utils import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/google/login')
def google_login():
    """
    Initiates the Google OAuth flow
    """
    from flask import current_app as app
    
    # Generate state token to prevent CSRF
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    # Construct Google OAuth URL
    auth_params = {
        'client_id': app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri': app.config['GOOGLE_REDIRECT_URI'],
        'scope': 'email profile',
        'state': state,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    params_str = '&'.join([f"{key}={val}" for key, val in auth_params.items()])
    auth_url = f"{app.config['GOOGLE_AUTH_URL']}?{params_str}"
    
    return redirect(auth_url)

@auth_bp.route('/google/callback')
def google_callback():
    """
    Callback endpoint for Google OAuth
    """
    from flask import current_app as app
    
    # Verify state token to prevent CSRF
    if request.args.get('state') != session.get('oauth_state'):
        return jsonify({'error': 'Invalid state parameter'}), 400
    
    # Exchange authorization code for tokens
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Authorization code not provided'}), 400
    
    # Request access token
    token_data = {
        'code': code,
        'client_id': app.config['GOOGLE_CLIENT_ID'],
        'client_secret': app.config['GOOGLE_CLIENT_SECRET'],
        'redirect_uri': app.config['GOOGLE_REDIRECT_URI'],
        'grant_type': 'authorization_code'
    }
    
    token_response = requests.post(app.config['GOOGLE_TOKEN_URL'], data=token_data)
    if not token_response.ok:
        return jsonify({'error': 'Failed to obtain access token'}), 400
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')
    
    # Get user info from Google
    user_info_response = requests.get(
        app.config['GOOGLE_USER_INFO_URL'],
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    if not user_info_response.ok:
        return jsonify({'error': 'Failed to obtain user info'}), 400
    
    user_info = user_info_response.json()
    
    # Extract user details
    google_id = user_info.get('id')
    email = user_info.get('email')
    name = user_info.get('name')
    
    # Check if user exists in Appwrite
    try:
        database_service = get_database_service()
        
        # Try to find user by email
        existing_users = database_service.list_documents(
            database_id=app.config['APPWRITE_DATABASE_ID'],
            collection_id=app.config['APPWRITE_USER_COLLECTION_ID'],
            queries=[f'email={email}']
        )
        
        user_data = {
            'name': name,
            'email': email,
            'googleId': google_id,
            'role': 'USER',
            'interests': [],
            'preferences': []
        }
        
        if existing_users.get('total', 0) > 0:
            # Update existing user
            user_doc = existing_users.get('documents')[0]
            user_id = user_doc.get('$id')
            
            database_service.update_document(
                database_id=app.config['APPWRITE_DATABASE_ID'],
                collection_id=app.config['APPWRITE_USER_COLLECTION_ID'],
                document_id=user_id,
                data=user_data
            )
        else:
            # Create new user in Appwrite
            user_id = ID.unique()
            database_service.create_document(
                database_id=app.config['APPWRITE_DATABASE_ID'],
                collection_id=app.config['APPWRITE_USER_COLLECTION_ID'],
                document_id=user_id,
                data=user_data
            )
        
        # Set session
        session['user_id'] = user_id
        session['email'] = email
        session['name'] = name
        
        # Redirect to frontend with success
        return redirect(f"/auth/success?user_id={user_id}")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/success')
def auth_success():
    """
    Success endpoint after successful authentication
    """
    user_id = request.args.get('user_id')
    return jsonify({
        'success': True,
        'message': 'Authentication successful',
        'user_id': user_id
    })

@auth_bp.route('/logout')
def logout():
    """
    Logout endpoint
    """
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})