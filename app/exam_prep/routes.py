from flask import Blueprint, jsonify, request
from app.core.core import ExamPrepAgent
from config import Config
from . import examprep_bp

@examprep_bp.route('/', methods=['POST'])
def exam_prep_endpoint():
    # Get JSON data from the request body
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body is required."}), 400

    # Retrieve parameters from the JSON payload
    board = data.get('board')
    class_level = data.get('class_level')
    subject = data.get('subject')
    department = data.get('department')

    # Validate that all parameters are provided
    missing_params = [param for param in ['board', 'class_level', 'subject', 'department'] if not data.get(param)]
    if missing_params:
        return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

    # Instantiate the ExamPrepAgent using configuration keys
    exam = ExamPrepAgent(
        Config.GROQ_API_FETCH_PAPER_KEY,
        Config.GROQ_API_ANALYSE_PAPER_KEY,
        Config.GROQ_API_GENERATE_QUERY_KEY,
        Config.GROQ_API_RESPONSE_STRUCTURE_KEY,
        Config.YOUTUBE_API_KEY
        
    )
    
    # Process the workflow using the parameters provided in the JSON body
    result = exam.process_workflow(
        board=board,
        class_level=class_level,
        subject=subject,
        department=department
    )
    
    return jsonify(result)