# app/routes.py
from flask import Blueprint, jsonify, request
from app.services import get_documents

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"message": "Welcome to RapidRevise Backend!"})

# Example endpoint to fetch all users from Appwrite
@main.route('/users', methods=['GET'])
def get_users():
    try:
        # Retrieve documents from the User collection
        users = get_documents(collection='User')
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
