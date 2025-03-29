from flask import Blueprint, jsonify
from app.auth.utils import login_required
from app.models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home_screen():
    return ("Welcome to RapidRevise-Backend")

@main_bp.route('/user/me')
@login_required
def get_current_user():
    """
    Get current authenticated user
    """
    from flask import session
    
    try:
        user_id = session.get('user_id')
        user_doc = User.get_by_id(user_id)
        
        if not user_doc:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'id': user_doc.get('$id'),
            'name': user_doc.get('name'),
            'email': user_doc.get('email'),
            'profile_picture': user_doc.get('profile_picture'),
            'role': user_doc.get('role'),
            'interests': user_doc.get('interests'),
            'preferences': user_doc.get('preferences')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500