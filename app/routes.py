# app/routes.py
import json
import os
from flask import Blueprint, jsonify
from app.core.core import ExamPrepAgent
from app.services import get_documents

main = Blueprint('main', __name__)


@main.route('/')
def index():
    # response = getModelResponse(
    #     user_prompt="I want to learn operating system in 1 day so I can pass my exam.")
    agent = ExamPrepAgent(
        groq_api_key=os.environ.get(
            "FIREWORKS_API_KEY") or "fw_3ZJRHBDE5QwVv3KTdfP6piKw",
        youtube_api_key=os.environ.get(
            "YOUTUBE_API_KEY") or "AIzaSyBONOTiEgoajQihP8-V7qaTlmH-0Nofkg0"
    )

    # Run the complete workflow
    result = agent.process_workflow(
        board="CBSE",
        class_level="12th",
        department="Science",
        subject="Biology"
    )

    print(json.dumps(result, indent=2))
    return jsonify({"result": result})

# Example endpoint to fetch all users from Appwrite


@main.route('/users', methods=['GET'])
def get_users():
    try:
        # Retrieve documents from the User collection
        users = get_documents(collection='User')
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
