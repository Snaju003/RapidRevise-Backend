from flask import Blueprint, jsonify, request
from app.core.core import ExamPrepAgent
from config import Config
from . import examprep_bp

@examprep_bp.route('/', methods=['GET'])
def exam_prep_endpoint():
    # Retrieve query parameters from the URL
    board = request.args.get('board')
    class_level = request.args.get('class_level')
    subject = request.args.get('subject')
    department = request.args.get('department')

    # Validate that all parameters are provided
    missing_params = []
    if not board:
        missing_params.append('board')
    if not class_level:
        missing_params.append('class_level')
    if not subject:
        missing_params.append('subject')
    if not department:
        missing_params.append('department')
    if missing_params:
        return jsonify({"error": f"Missing query parameters: {', '.join(missing_params)}"}), 400

    # Instantiate the ExamPrepAgent with required API keys
    exam = ExamPrepAgent(
        Config.GROQ_API_FETCH_PAPER_KEY,
        Config.GROQ_API_ANALYSE_PAPER_KEY,
        Config.GROQ_API_GENERATE_QUERY_KEY,
        Config.GROQ_API_RESPONSE_STRUCTURE_KEY,
        "AIzaSyBONOTiEgoajQihP8-V7qaTlmH-0Nofkg0"
    )
    # Process the workflow using parameters provided by the user
    result = exam.process_workflow(
        board=board,
        class_level=class_level,
        subject=subject,
        department=department
    )
    return jsonify(result)