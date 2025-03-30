import os
from flask import Blueprint, jsonify
from app.auth.utils import login_required
from app.core.pdf_file_reader import RagService
from app.models.user import User

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home_screen():
    # Example usage:
    rag_service = RagService()
    # Replace 'data/event_data.pdf' with the actual path to your PDF file.
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(BASE_DIR, "data", "sem6.pdf")
    rag_service.initialize(pdf_path)
    print("Initialized")
    prompt = "I've exam on Networking layer, Physcial layer tomorrow....I want to study just to pass the exam...Which topics do I need to study??"
    context = rag_service.get_context(prompt)
    res = rag_service.generate_response(prompt, context)
    return jsonify({'message': str(res)})
    # return ("Welcome to RapidRevise-Backend")


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
